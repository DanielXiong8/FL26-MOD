# -*- coding: utf-8 -*-
"""validate_mutation.py — prove ONLY target player changed between original & modified bundles."""
import io, struct, sys
import UnityPy

ORIG = r"C:\FL26_Mod\extracted\assets_bundles_gamedata.unity3d"
MOD  = r"C:\FL26_Mod\modified\assets_bundles_gamedata.unity3d"
TARGET = 100373

def load_players(path):
    with open(path, "rb") as f:
        env = UnityPy.load(io.BytesIO(f.read()))
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read(check_read=False)
            if getattr(d, "m_Name", "") == "Players":
                raw = getattr(d, "m_Script", b"")
                if isinstance(raw, str): raw = raw.encode("utf-8", errors="surrogateescape")
                return env, bytes(raw)
    raise RuntimeError("Players not found")

def parse(raw):
    off = 8
    ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
    for _ in range(ncnt):
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
    pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
    recs = {}
    for _ in range(pcnt):
        start = off
        pid = struct.unpack_from("<I", raw, off)[0]; off += 4
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
        off += 8 + 3 + 17 + 3 + 4
        recs[pid] = raw[start:off]
    return recs

def main():
    env_o, raw_o = load_players(ORIG)
    env_m, raw_m = load_players(MOD)
    # 1. object counts identical?
    n_o = len(list(env_o.objects)); n_m = len(list(env_m.objects))
    print(f"bundle objects: orig={n_o} mod={n_m} same={n_o==n_m}")
    # 2. per-player record diff
    ro = parse(raw_o); rm = parse(raw_m)
    print(f"player records: orig={len(ro)} mod={len(rm)}")
    diff = [pid for pid in ro if ro[pid] != rm.get(pid)]
    print(f"changed records: {len(diff)} -> {diff}")
    ok = diff == [TARGET]
    print(f"ONLY target changed: {ok}")
    # 3. other TextAssets identical? (sample: Teams, ClubPlayer, PlayerAppearanceTable, StarPlayerAppearance)
    def get_ta(env, name):
        for o in env.objects:
            if o.type.name == "TextAsset":
                d = o.read(check_read=False)
                if getattr(d, "m_Name", "") == name:
                    r = getattr(d, "m_Script", b"")
                    if isinstance(r, str): r = r.encode("utf-8", errors="surrogateescape")
                    return bytes(r)
        return None
    for tn in ("Teams", "ClubPlayer", "PlayerAppearanceTable", "StarPlayerAppearance", "GlobalTables"):
        a, b = get_ta(env_o, tn), get_ta(env_m, tn)
        print(f"  {tn}: identical={a == b} ({len(a)}B)")
    # 4. target new content readable
    import re
    rec = rm[TARGET]
    ln = struct.unpack_from("<H", rec, 4)[0]
    name = rec[6:6+ln*2].decode("utf-16-le")
    attrs = list(rec[6+ln*2+8+3 : 6+ln*2+8+3+17])
    print(f"target now: name={name!r} attrs={attrs[:6]}...")
    print("VALIDATION", "PASS" if ok else "FAIL")

if __name__ == "__main__":
    sys.exit(main())
