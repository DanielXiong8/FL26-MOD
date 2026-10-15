# -*- coding: utf-8 -*-
"""diff_summary.py — quick diff summary between static and career player_blob."""
import sqlite3

SDB = r"C:\FL26_Mod\saves\working\Static\static.db"
CDB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"

sdb = sqlite3.connect(f"file:{SDB}?mode=ro&immutable=1", uri=True)
cdb = sqlite3.connect(f"file:{CDB}?mode=ro&immutable=1", uri=True)

scur = sdb.cursor()
ccur = cdb.cursor()

# Static tables
scur.execute("SELECT name FROM sqlite_master WHERE type='table'")
stables = [r[0] for r in scur.fetchall()]
print(f"static.db tables: {stables}")
for t in stables:
    scur.execute(f"SELECT COUNT(*) FROM [{t}]")
    print(f"  {t}: {scur.fetchone()[0]} rows")

# Check if player_blob exists in static
if "player_blob" in stables:
    scur.execute("SELECT player_id, payload FROM player_blob")
    static_p = {r[0]: r[1] for r in scur.fetchall()}
    ccur.execute("SELECT player_id, payload FROM player_blob")
    career_p = {r[0]: r[1] for r in ccur.fetchall()}

    modified = [pid for pid in career_p if pid in static_p and career_p[pid] != static_p[pid]]
    new_p = [pid for pid in career_p if pid not in static_p]
    removed = [pid for pid in static_p if pid not in career_p]

    print(f"\nstatic players: {len(static_p)}")
    print(f"career players: {len(career_p)}")
    print(f"modified: {len(modified)}")
    print(f"new: {len(new_p)}")
    print(f"removed: {len(removed)}")
    
    if modified:
        print(f"\nmodified IDs: {modified[:20]}")
        for pid in modified[:3]:
            print(f"\n  pid={pid}:")
            print(f"    static: {static_p[pid].hex()}")
            print(f"    career: {career_p[pid].hex()}")
    
    if new_p:
        print(f"\nnew IDs (first 20): {new_p[:20]}")
        # Check if any new player has Bailey name
        for pid in new_p:
            if b"Bailey" in career_p[pid] or b"BAILEY" in career_p[pid]:
                print(f"  *** pid={pid} contains Bailey! ***")

# Check archive_blob diff
if "archive_blob" in stables:
    scur.execute("SELECT payload FROM archive_blob WHERE id=1")
    sarch = scur.fetchone()
    ccur.execute("SELECT payload FROM archive_blob WHERE id=1")
    carch = ccur.fetchone()
    if sarch and carch:
        print(f"\narchive_blob: static={len(sarch[0])}B vs career={len(carch[0])}B")
        if sarch[0] != carch[0]:
            print("  DIFFERENT")
        else:
            print("  IDENTICAL")

sdb.close()
cdb.close()
