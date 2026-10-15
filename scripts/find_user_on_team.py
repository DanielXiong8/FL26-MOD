# -*- coding: utf-8 -*-
"""find_user_on_team.py — decode team 20044 roster + find UserPlayer."""
import sqlite3, sys, os
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields

DB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

# Team 20044 (user's team)
print("=== team_blob team_id=20044 ===")
cur.execute("SELECT payload FROM team_blob WHERE team_id=20044")
row = cur.fetchone()
if row:
    fields = decode_message(row[0], max_depth=3)
    for line in format_fields(fields):
        print(line)

# All players on team 20044 (from player_blob where f5=20044)
print("\n=== players on team 20044 ===")
cur.execute("SELECT player_id, payload FROM player_blob")
for pid, payload in cur.fetchall():
    fields = decode_message(payload, max_depth=2)
    # Check f5 (team_id)
    for f in fields:
        if f[0] == 5 and f[1] == "varint" and f[2] == 20044:
            # Get name from f9.f1
            for f2 in fields:
                if f2[0] == 9 and f2[1] == "message":
                    for f3 in f2[2]:
                        if f3[0] == 1 and f3[1] == "string":
                            # Get position from f4
                            pos = None
                            for f4 in fields:
                                if f4[0] == 4 and f4[1] == "varint":
                                    pos = f4[2]
                            print(f"  pid={pid}: {f3[2]!r} pos={pos}")
            break

conn.close()
