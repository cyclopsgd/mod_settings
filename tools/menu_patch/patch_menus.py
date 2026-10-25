"""Register MenuScenario_ModSettings in the 2.5 pregame menu and repack ModSettings.archive.

PR #34 rebuilt menu.inkmenu and pregame_menu.inkmenu from the game 2.5 originals with
mod_settings_main added, but the pregame copy lost the MenuScenario_ModSettings scenario
that 0.2.21 registered after MenuScenario_Settings. Without it the main menu's Mods button
switches to a scenario the menu system does not know.

usage (from the repository root):
  python tools/menu_patch/patch_menus.py            patch the source file and the packed archive
  python tools/menu_patch/patch_menus.py --check    only print what the files contain
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr2w import CR2W  # noqa: E402
from rdar import Archive  # noqa: E402

SOURCE = "src/wolvenkit/source/archive"
ARCHIVE = "src/wolvenkit/packed/archive/pc/mod/ModSettings.archive"
PREGAME = r"base\gameplay\gui\fullscreen\main_menu\pregame_menu.inkmenu"
MENU = r"base\gameplay\gui\fullscreen\menu.inkmenu"
SCENARIO = "MenuScenario_ModSettings"
AFTER = "MenuScenario_Settings"


def source_path(depot):
    return os.path.join(SOURCE, *depot.split("\\"))


def menu_resource(f: CR2W):
    if len(f.exports) != 1 or f.name(f.exports[0]["cls"]) != "inkMenuResource":
        raise SystemExit("expected one inkMenuResource export")
    blob = f.exports[0]["data"]
    props, end = f.parse_props(blob)
    if end != len(blob):
        raise SystemExit("unexpected data after the property list")
    return blob, {p["name"]: p for p in props}


def cname_array(f, blob, prop):
    vs = prop["value_start"]
    n = struct.unpack_from("<I", blob, vs)[0]
    return [f.name(struct.unpack_from("<H", blob, vs + 4 + 2 * i)[0]) for i in range(n)]


def menu_entries(f, blob, prop):
    vs = prop["value_start"]
    n = struct.unpack_from("<I", blob, vs)[0]
    pos, out = vs + 4, []
    for _ in range(n):
        props, pos = f.parse_props(blob, pos)
        entry = {"name": "", "depth": 0}
        for p in props:
            if p["name"] == "name":
                entry["name"] = f.name(struct.unpack_from("<H", blob, p["value_start"])[0])
            elif p["name"] == "depth":
                entry["depth"] = struct.unpack_from("<I", blob, p["value_start"])[0]
        out.append(entry)
    return out


def describe(label, data):
    f = CR2W(data)
    blob, props = menu_resource(f)
    entries = menu_entries(f, blob, props["menusEntries"])
    scenarios = cname_array(f, blob, props["scenariosNames"])
    mod = [(i, e["depth"]) for i, e in enumerate(entries) if e["name"] == "mod_settings_main"]
    print(f"{label}: {len(entries)} menu entries, mod_settings_main (index, depth) {mod}; "
          f"{len(scenarios)} scenarios, {SCENARIO} at "
          f"{scenarios.index(SCENARIO) if SCENARIO in scenarios else 'missing'}")
    return scenarios


def add_scenario(data: bytes) -> bytes:
    f = CR2W(data)
    blob, props = menu_resource(f)
    prop = props["scenariosNames"]
    if prop["type"] != "array:CName":
        raise SystemExit(f"scenariosNames is {prop['type']}")
    scenarios = cname_array(f, blob, prop)
    if SCENARIO in scenarios:
        return data
    at = scenarios.index(AFTER) + 1
    idx = f.name_index(SCENARIO)
    if idx < 0:
        f.names.append(SCENARIO)
        idx = len(f.names) - 1
    vs = prop["value_start"]
    new = bytearray(blob)
    new[vs + 4 + 2 * at:vs + 4 + 2 * at] = struct.pack("<H", idx)
    struct.pack_into("<I", new, vs, len(scenarios) + 1)
    size_at = prop["start"] + 4
    struct.pack_into("<I", new, size_at, struct.unpack_from("<I", blob, size_at)[0] + 2)
    f.exports[0]["data"] = bytes(new)
    out = f.build()

    # every other property must come through unchanged
    g = CR2W(out)
    gblob, gprops = menu_resource(g)
    assert cname_array(g, gblob, gprops["scenariosNames"]) == scenarios[:at] + [SCENARIO] + scenarios[at:]
    for name, p in props.items():
        if name != "scenariosNames":
            q = gprops[name]
            assert blob[p["start"]:p["value_end"]] == gblob[q["start"]:q["value_end"]], name
    return out


def main():
    check_only = "--check" in sys.argv
    pregame_file = source_path(PREGAME)
    pregame = open(pregame_file, "rb").read()
    describe("source pregame_menu.inkmenu", pregame)
    describe("source menu.inkmenu", open(source_path(MENU), "rb").read())
    archive = Archive(open(ARCHIVE, "rb").read())
    if not archive.index_crc_ok():
        raise SystemExit("archive index checksum does not match; refusing to rewrite it")
    if archive.write() != archive.raw:
        raise SystemExit("archive does not round-trip; refusing to rewrite it")
    if check_only:
        seg = archive.segments[archive.file(PREGAME)["seg_start"]]
        if seg["zsize"] == seg["size"]:
            describe("packed pregame_menu.inkmenu", archive.segment_bytes(seg))
        else:
            print("packed pregame_menu.inkmenu is Kraken-compressed (not inspected)")
        return
    patched = add_scenario(pregame)
    if patched == pregame:
        print("source already registers the scenario")
    else:
        open(pregame_file, "wb").write(patched)
        describe("patched pregame_menu.inkmenu", patched)
    out = archive.write({PREGAME: patched})
    open(ARCHIVE, "wb").write(out)
    check = Archive(out)
    assert check.index_crc_ok()
    assert check.segment_bytes(check.segments[check.file(PREGAME)["seg_start"]]) == patched
    print(f"{ARCHIVE}: {len(archive.raw)} -> {len(out)} bytes")


if __name__ == "__main__":
    main()
