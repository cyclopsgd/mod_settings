"""Minimal Cyberpunk 2077 .archive (RDAR version 12) reader and segment-replacing writer.

Writing an unmodified archive reproduces the WolvenKit output byte for byte:
- the header and custom data (LXRS path list) before the first segment are copied
- segments are laid out back to back in their original order
- the index starts on a 4 KiB boundary and the file ends on one, padded with 0xD9
- the index checksum is CRC-64/XZ over the index after its crc field
Replacement data is stored uncompressed (zSize == size), which the game reads as is.
"""
import struct

HDR_FMT = "<4sIQIQIQ"  # magic, version, indexPos, indexSize, debugPos, debugSize, fileSize
ALIGN = 0x1000
PAD = b"\xd9"
M64 = (1 << 64) - 1


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & M64
    return h


def path_hash(depot_path: str) -> int:
    return fnv1a64(depot_path.lower().replace("/", "\\").encode("utf-8"))


def _crc64_xz_table():
    table = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xC96C5795D7870F42 if c & 1 else c >> 1
        table.append(c)
    return table


_CRC64 = _crc64_xz_table()


def crc64_xz(data: bytes) -> int:
    c = M64
    for b in data:
        c = _CRC64[(c ^ b) & 0xFF] ^ (c >> 8)
    return c ^ M64


def _align(n):
    return (n + ALIGN - 1) // ALIGN * ALIGN


class Archive:
    def __init__(self, data: bytes):
        self.raw = data
        (magic, self.version, self.index_pos, self.index_size, self.debug_pos, self.debug_size,
         self.file_size) = struct.unpack_from(HDR_FMT, data, 0)
        if magic != b"RDAR":
            raise ValueError("not an RDAR archive")
        p = self.index_pos
        self.ft_offset, self.ft_size, self.index_crc, n_files, n_segs, n_deps = struct.unpack_from("<IIQIII", data, p)
        q = p + 28
        self.files = []
        for _ in range(n_files):
            h, ts, n_inline, s0, s1, d0, d1 = struct.unpack_from("<QqIIIII", data, q)
            self.files.append(dict(hash=h, timestamp=ts, n_inline=n_inline, seg_start=s0, seg_end=s1,
                                   dep_start=d0, dep_end=d1, sha1=data[q + 36:q + 56]))
            q += 56
        self.segments = []
        for _ in range(n_segs):
            off, zsize, size = struct.unpack_from("<QII", data, q)
            self.segments.append(dict(offset=off, zsize=zsize, size=size))
            q += 16
        self.deps = list(struct.unpack_from(f"<{n_deps}Q", data, q))

    def segment_bytes(self, seg):
        return self.raw[seg["offset"]:seg["offset"] + seg["zsize"]]

    def index_crc_ok(self):
        body = self.raw[self.index_pos + 16:self.index_pos + 8 + self.ft_size]
        return crc64_xz(body) == self.index_crc

    def file(self, depot_path):
        h = path_hash(depot_path)
        return next((f for f in self.files if f["hash"] == h), None)

    def write(self, replacements=None) -> bytes:
        """replacements: {depot path: bytes} for files stored as a single segment."""
        repl = {}
        for depot, blob in (replacements or {}).items():
            f = self.file(depot)
            if f is None:
                raise KeyError(f"{depot} is not in the archive")
            if f["seg_end"] - f["seg_start"] != 1 or f["n_inline"]:
                raise ValueError(f"{depot} has buffer segments")
            repl[f["seg_start"]] = blob
        out = bytearray(self.raw[:min(s["offset"] for s in self.segments)])
        segs = [None] * len(self.segments)
        for si in sorted(range(len(self.segments)), key=lambda i: self.segments[i]["offset"]):
            s = self.segments[si]
            blob = repl.get(si)
            if blob is None:
                blob = self.segment_bytes(s)
                segs[si] = (len(out), s["zsize"], s["size"])
            else:
                segs[si] = (len(out), len(blob), len(blob))
            out += blob
        out += PAD * (_align(len(out)) - len(out))
        index_pos = len(out)
        body = struct.pack("<III", len(self.files), len(segs), len(self.deps))
        for f in self.files:
            body += struct.pack("<QqIIIII", f["hash"], f["timestamp"], f["n_inline"], f["seg_start"], f["seg_end"],
                                f["dep_start"], f["dep_end"]) + f["sha1"]
        body += b"".join(struct.pack("<QII", *s) for s in segs)
        body += b"".join(struct.pack("<Q", d) for d in self.deps)
        index = struct.pack("<IIQ", self.ft_offset, 8 + len(body), crc64_xz(body)) + body
        out += index
        out += PAD * (_align(len(out)) - len(out))
        struct.pack_into(HDR_FMT, out, 0, b"RDAR", self.version, index_pos, len(index), self.debug_pos,
                         self.debug_size, len(out))
        return bytes(out)
