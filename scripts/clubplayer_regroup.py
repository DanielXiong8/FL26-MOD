# -*- coding: utf-8 -*-
"""ClubPlayer regroup: does payload group by RECORD team_id? Compare vs header sizes."""
import csv, struct, sys, io, zipfile
from collections import Counter, OrderedDict
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def load_textasset(env, want):
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read(check_read=False)
            if getattr(d, "m_Name", "") == want:
                raw = getattr(d, "m_Script", b"")
                if isinstance(raw, str):
                    raw = raw.encode("utf-8", errors="surrogateescape")
                return bytes(raw)
    raise KeyError(want)

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    craw = load_textasset(env, "ClubPlayer")

    tcnt = struct.unpack_from("<I", craw, 0)[0]
    hdr = [struct.unpack_from("<II", craw, 4 + i*8) for i in range(tcnt)]
    off = 4 + tcnt * 8
    recs = []
    for _ in range(sum(s for _, s in hdr)):
        tid, pid = struct.unpack_from("<II", craw, off)
        recs.append((tid, pid, craw[off+8], craw[off+13]))
        off += 17

    # Q1: is payload contiguously grouped by record team_id?
    switches = sum(1 for i in range(1, len(recs)) if recs[i][0] != recs[i-1][0])
    print(f"records={len(recs)} team_id switches={switches} (contiguous grouping => switches == teams-1 = {tcnt-1})")

    # run-length groups
    groups = []
    cur, cnt = recs[0][0], 1
    for r in recs[1:]:
        if r[0] == cur: cnt += 1
        else: groups.append((cur, cnt)); cur, cnt = r[0], 1
    groups.append((cur, cnt))
    print(f"payload groups={len(groups)}")

    # compare payload group sizes vs header
    hmap = {t: s for t, s in hdr}
    gmap = {t: s for t, s in groups}
    match = sum(1 for t, s in gmap.items() if hmap.get(t) == s)
    print(f"header size == payload group size: {match}/{len(gmap)}")
    print(f"header teams == payload teams set: {set(hmap) == set(gmap)}")

    # Fulham 20367: header says?
    print(f"\nFulham 20367: header size={hmap.get(20367)} payload group size={gmap.get(20367)}")

    # Fulham payload records (grouped by RECORD team_id)
    ful = [r for r in recs if r[0] == 20367]
    players = {r["player_id"]: r for r in csv.DictReader(open(r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon\03_player\player_registry_candidates.csv", encoding="utf-8-sig"))}
    print(f"Fulham records by record.team_id: {len(ful)}")
    for t, p, jersey, role in ful[:15]:
        nm = players.get(str(p), {}).get("name", "?")
        print(f"  pid={p:<7} {nm:<20} #{jersey:>2} role={role}")

if __name__ == "__main__":
    sys.exit(main())
