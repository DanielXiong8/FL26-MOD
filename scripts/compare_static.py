# -*- coding: utf-8 -*-
"""compare_static.py — compare static.db vs career save player_blob."""
import sqlite3, sys, os
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields

SDB = r"C:\FL26_Mod\saves\working\Static\static.db"
CDB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"

# Static DB
sdb = sqlite3.connect(f"file:{SDB}?mode=ro&immutable=1", uri=True)
scur = sdb.cursor()
scur.execute("SELECT name FROM sqlite_master WHERE type='table'")
stables = [r[0] for r in scur.fetchall()]
print(f"static.db tables: {stables}")
for t in stables:
    scur.execute(f"SELECT COUNT(*) FROM [{t}]")
    print(f"  {t}: {scur.fetchone()[0]} rows")

# player_id=1 in static
if "player_blob" in stables:
    scur.execute("SELECT player_id, payload FROM player_blob WHERE player_id=1")
    r = scur.fetchone()
    if r:
        print(f"\nstatic player_id=1: {len(r[1])}B")
        print(f"hex: {r[1].hex()}")
        fields = decode_message(r[1], max_depth=3)
        for line in format_fields(fields):
            print(f"  {line}")

# Career DB player_id=1
cdb = sqlite3.connect(f"file:{CDB}?mode=ro&immutable=1", uri=True)
ccur = cdb.cursor()
ccur.execute("SELECT player_id, payload FROM player_blob WHERE player_id=1")
r2 = ccur.fetchone()
print(f"\ncareer player_id=1: {len(r2[1])}B")
print(f"hex: {r2[1].hex()}")

# Compare
if r and r2:
    if r[1] == r2[1]:
        print("\nplayer_id=1: IDENTICAL to static")
    else:
        print(f"\nplayer_id=1: DIFFERENT! static={len(r[1])}B vs career={len(r2[1])}B")
        # find first difference
        for i, (a, b) in enumerate(zip(r[1], r2[1])):
            if a != b:
                print(f"  first diff at offset {i}: 0x{a:02x} vs 0x{b:02x}")
                break

# Check for any modified players (compare all)
if "player_blob" in stables:
    scur.execute("SELECT player_id, payload FROM player_blob")
    static_players = {r[0]: r[1] for r in scur.fetchall()}
    ccur.execute("SELECT player_id, payload FROM player_blob")
    career_players = {r[0]: r[1] for r in ccur.fetchall()}
    
    # Find differences
    modified = []
    new_players = []
    removed = []
    for pid, payload in career_players.items():
        if pid not in static_players:
            new_players.append(pid)
        elif static_players[pid] != payload:
            modified.append(pid)
    for pid in static_players:
        if pid not in career_players:
            removed.append(pid)
    
    print(f"\n=== DIFF ANALYSIS ===")
    print(f"static players: {len(static_players)}")
    print(f"career players: {len(career_players)}")
    print(f"modified: {len(modified)}")
    print(f"new: {len(new_players)}")
    print(f"removed: {len(removed)}")
    if modified:
        print(f"modified IDs (first 20): {modified[:20]}")
    if new_players:
        print(f"new IDs: {new_players}")
        for pid in new_players:
            payload = career_players[pid]
            fields = decode_message(payload, max_depth=3)
            print(f"\n  NEW player_id={pid} ({len(payload)}B):")
            for line in format_fields(fields, 2):
                print(f"  {line}")

sdb.close()
cdb.close()
