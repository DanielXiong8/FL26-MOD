# -*- coding: utf-8 -*-
"""
modify_bundle.py — Mutation POC: modify ONE test player inside gamedata.unity3d.
Reads extracted bundle, writes modified bundle to C:\FL26_Mod\modified\.
Only touches TextAsset 'Players'. Byte-exact re-serialization of plyrcsv0.
"""
import io, json, os, struct, sys
import UnityPy

SRC = r"C:\FL26_Mod\extracted\assets_bundles_gamedata.unity3d"
DST_DIR = r"C:\FL26_Mod\modified"
LOGS = r"C:\FL26_Mod\logs"

TARGET_PID = 100373          # 'Reno', Fulham(20367) #1 GK role=0 — in-game visible starter (record.team_id authoritative)
NEW_NAME = "ZZModTest"       # <=20 chars
NEW_ATTRS = {i: 95 for i in range(17)}  # differential probe: all 17 attrs -> 95

def parse_plyrcsv0(raw: bytes):
    assert raw[:8] == b"plyrcsv0"
    off = 8
    ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
    nations = []
    for _ in range(ncnt):
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        nations.append(raw[off:off+ln*2]); off += ln*2
    pcnt_off = off
    pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
    recs = []
    for _ in range(pcnt):
        pid = struct.unpack_from("<I", raw, off)[0]; off += 4
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        name = raw[off:off+ln*2]; off += ln*2
        fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16 = struct.unpack_from("<H", raw, off)[0]; off += 2
        tail8 = raw[off]; off += 1
        year = struct.unpack_from("<I", raw, off)[0]; off += 4
        recs.append({"pid": pid, "name": name, "fa": fa, "fb": fb, "fc": fc, "nat": nat,
                     "b1": b1, "b16": b16, "b0": b0, "attrs": attrs,
                     "tail16": tail16, "tail8": tail8, "year": year})
    assert off == len(raw), f"parse not consumed: {off}/{len(raw)}"
    return raw[:8], nations, pcnt_off, recs

def serialize_plyrcsv0(magic, nations, recs) -> bytes:
    out = io.BytesIO()
    out.write(magic)
    out.write(struct.pack("<H", len(nations)))
    for nb in nations:
        out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
    out.write(struct.pack("<I", len(recs)))
    for r in recs:
        out.write(struct.pack("<I", r["pid"]))
        nb = r["name"]
        out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
        out.write(struct.pack("<HHHH", r["fa"], r["fb"], r["fc"], r["nat"]))
        out.write(bytes([r["b1"], r["b16"], r["b0"]]))
        out.write(bytes(r["attrs"]))
        out.write(struct.pack("<H", r["tail16"]))
        out.write(bytes([r["tail8"]]))
        out.write(struct.pack("<I", r["year"]))
    return out.getvalue()

def main():
    os.makedirs(DST_DIR, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
    with open(SRC, "rb") as f:
        bundle = f.read()
    env = UnityPy.load(io.BytesIO(bundle))
    target = None
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read(check_read=False)
            if getattr(d, "m_Name", "") == "Players":
                target = (o, d); break
    if not target: raise RuntimeError("Players TextAsset not found")
    obj, tobj = target
    raw = getattr(tobj, "m_Script", b"")
    if isinstance(raw, str): raw = raw.encode("utf-8", errors="surrogateescape")
    raw = bytes(raw)

    magic, nations, pcnt_off, recs = parse_plyrcsv0(raw)
    hit = [r for r in recs if r["pid"] == TARGET_PID]
    if not hit: raise RuntimeError(f"pid {TARGET_PID} not found")
    r = hit[0]
    before = {
        "pid": r["pid"],
        "name": r["name"].decode("utf-16-le"),
        "unk_a": r["fa"], "unk_b": r["fb"], "unk_c": r["fc"], "nation_idx": r["nat"],
        "unk_pos": r["b1"], "attrs": list(r["attrs"]), "unk_tail": r["tail16"], "year": r["year"],
    }
    # mutate
    r["name"] = NEW_NAME.encode("utf-16-le")
    for i, v in NEW_ATTRS.items():
        r["attrs"][i] = v
    after = {"name": NEW_NAME, "attrs": {f"attr_{i:02d}": v for i, v in NEW_ATTRS.items()}}

    new_raw = serialize_plyrcsv0(magic, nations, recs)
    # structural self-check: reparse
    parse_plyrcsv0(new_raw)
    print(f"old size={len(raw):,} new size={len(new_raw):,} delta={len(new_raw)-len(raw)}")

    tobj.m_Script = new_raw.decode("utf-8", errors="surrogateescape")
    tobj.save()
    out_bundle = env.file.save(packer="lz4")
    if isinstance(out_bundle, (bytes, bytearray)):
        out_bytes = bytes(out_bundle)
    else:
        out_bytes = out_bundle.read() if hasattr(out_bundle, "read") else bytes(out_bundle)
    dst = os.path.join(DST_DIR, "assets_bundles_gamedata.unity3d")
    with open(dst, "wb") as f:
        f.write(out_bytes)
    print(f"modified bundle -> {dst} ({len(out_bytes):,} bytes)")

    with open(os.path.join(LOGS, "mutation_record.json"), "w", encoding="utf-8") as f:
        json.dump({"target_pid": TARGET_PID, "before": before, "after": after,
                   "old_bundle_bytes": len(bundle), "new_bundle_bytes": len(out_bytes)},
                  f, ensure_ascii=False, indent=2)
    print("before:", json.dumps(before, ensure_ascii=False))
    print("after :", json.dumps(after, ensure_ascii=False))
    print("MUTATION OK")

if __name__ == "__main__":
    sys.exit(main())
