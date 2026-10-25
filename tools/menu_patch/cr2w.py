"""Minimal CR2W (Cyberpunk 2077, version 195) reader/writer for buffer-less resources such as .inkmenu.

Reads the header, the table descriptors and the string/name/import/property/export/embedded
tables, parses export property lists, and writes the file back with recomputed offsets and
checksums. Writing an unmodified file reproduces the WolvenKit output byte for byte:
- names-table hash: FNV-1a 64 of the name folded to 32 bits (0 for the empty name)
- table checksums: CRC32 of each table
- header checksum: CRC32 of header + table descriptors with the crc field set to 0xDEADBEEF
- export crc and the header's numChunks field are kept as read
"""
import struct
import sys
import zlib

MAGIC = b"CR2W"
HEADER_FMT = "<4sIIQIIIII"  # magic, version, flags, timestamp, buildVersion, objectsEnd, buffersEnd, crc32, numChunks
HEADER_SIZE = struct.calcsize(HEADER_FMT)
TABLE_FMT = "<III"  # offset, itemCount (byte size for the string table), crc32
TABLES = 10


def fnv1a64(data: bytes) -> int:
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def name_hash(s: str) -> int:
    if not s:
        return 0
    h = fnv1a64(s.encode("utf-8"))
    return (h >> 32) ^ (h & 0xFFFFFFFF)


class CR2W:
    def __init__(self, data: bytes):
        hdr = struct.unpack_from(HEADER_FMT, data, 0)
        if hdr[0] != MAGIC:
            raise ValueError("not a CR2W file")
        (_, self.version, self.flags, self.timestamp, self.build_version, self.objects_end,
         self.buffers_end, self.crc32, self.num_chunks) = hdr
        self.tables = [struct.unpack_from(TABLE_FMT, data, HEADER_SIZE + i * 12) for i in range(TABLES)]
        off, size, _ = self.tables[0]
        self.strtab = data[off:off + size]
        off, cnt, _ = self.tables[1]
        self.names = [self._cstr(struct.unpack_from("<II", data, off + i * 8)[0]) for i in range(cnt)]
        off, cnt, _ = self.tables[2]
        self.imports = []  # (depot path, class name index, flags)
        for i in range(cnt):
            soff, cls, flags = struct.unpack_from("<IHH", data, off + i * 8)
            self.imports.append((self._cstr(soff), cls, flags))
        off, cnt, _ = self.tables[3]
        self.properties = [data[off + i * 16:off + (i + 1) * 16] for i in range(cnt)]
        off, cnt, _ = self.tables[4]
        self.exports = []
        for i in range(cnt):
            cls, flags, parent, dsize, doff, template, crc = struct.unpack_from("<HHIIIII", data, off + i * 24)
            self.exports.append(dict(cls=cls, flags=flags, parent=parent, template=template, crc=crc,
                                     data=bytes(data[doff:doff + dsize])))
        if self.tables[5][1]:
            raise ValueError("files with buffers are not supported")
        off, cnt, _ = self.tables[6]
        self.embedded = [data[off + i * 16:off + (i + 1) * 16] for i in range(cnt)]

    def _cstr(self, soff):
        return self.strtab[soff:self.strtab.index(b"\0", soff)].decode("utf-8")

    def name(self, idx):
        return self.names[idx]

    def name_index(self, s):
        return self.names.index(s) if s in self.names else -1

    def parse_props(self, blob, pos=0):
        """Parse a property list (zero byte, then nameIdx/typeIdx/size records, then a 0 name index)."""
        if blob[pos] != 0:
            raise ValueError(f"unexpected lead byte at {pos}")
        pos += 1
        out = []
        while True:
            nidx = struct.unpack_from("<H", blob, pos)[0]
            if nidx == 0:
                return out, pos + 2
            tidx, size = struct.unpack_from("<HI", blob, pos + 2)
            # size counts its own 4 bytes, so the value spans [pos + 8, pos + 4 + size)
            out.append(dict(name=self.name(nidx), type=self.name(tidx), start=pos,
                            value_start=pos + 8, value_end=pos + 4 + size))
            pos += 4 + size

    def build(self) -> bytes:
        strtab = bytearray()
        offsets = {}

        def add(s):
            if s not in offsets:
                offsets[s] = len(strtab)
                strtab.extend(s.encode("utf-8") + b"\0")
            return offsets[s]

        t_names = b"".join(struct.pack("<II", add(s), name_hash(s)) for s in self.names)
        t_imports = b"".join(struct.pack("<IHH", add(p), c, f) for p, c, f in self.imports)
        t_props = b"".join(self.properties)
        t_embedded = b"".join(self.embedded)
        pos = HEADER_SIZE + TABLES * 12
        layout = {}
        for idx, blob, count in ((0, strtab, len(strtab)), (1, t_names, len(self.names)),
                                 (2, t_imports, len(self.imports)), (3, t_props, len(self.properties))):
            layout[idx] = (pos, count, bytes(blob))
            pos += len(blob)
        exports_pos = pos
        pos += 24 * len(self.exports)
        embedded_pos = pos
        pos += len(t_embedded)
        t_exports = bytearray()
        chunks = bytearray()
        for e in self.exports:
            t_exports += struct.pack("<HHIIIII", e["cls"], e["flags"], e["parent"], len(e["data"]),
                                     pos + len(chunks), e["template"], e["crc"])
            chunks += e["data"]
        layout[4] = (exports_pos, len(self.exports), bytes(t_exports))
        layout[6] = (embedded_pos, len(self.embedded), t_embedded)
        end = pos + len(chunks)
        descs = []
        for i in range(TABLES):
            if i in layout and layout[i][1]:
                off, cnt, blob = layout[i]
                descs.append((off, cnt, zlib.crc32(blob) & 0xFFFFFFFF))
            else:
                descs.append((0, 0, 0))

        def header(crc):
            return struct.pack(HEADER_FMT, MAGIC, self.version, self.flags, self.timestamp, self.build_version,
                               end, end, crc, self.num_chunks) + b"".join(struct.pack(TABLE_FMT, *d) for d in descs)

        crc = zlib.crc32(header(0xDEADBEEF)) & 0xFFFFFFFF
        out = header(crc) + bytes(strtab) + t_names + t_imports + t_props + bytes(t_exports) + t_embedded + bytes(chunks)
        assert len(out) == end
        return out


if __name__ == "__main__":
    for path in sys.argv[1:]:
        raw = open(path, "rb").read()
        same = CR2W(raw).build() == raw
        print(f"{path}: round trip {'identical' if same else 'DIFFERS'}")
