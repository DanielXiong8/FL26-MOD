# -*- coding: utf-8 -*-
"""deep_inspect_user.py — find UserPlayer in archive_blob + player_blob."""
import sqlite3, re, os, struct, sys
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields

DB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
OUT = r"C:\FL26_Mod\recon\07_save"
conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

# 1. Archive blob context around "BAILEY"
cur.execute("SELECT payload FROM archive_blob WHERE id=1")
raw = cur.fetchone()[0]
idx = raw.find(b"BAILEY")
print(f"=== archive_blob @0x{idx:04x} context ===")
start = max(0, idx - 40)
end = min(len(raw), idx + 60)
chunk = raw[start:end]
print(f"hex: {chunk.hex()}")
print(f"ascii: {''.join(chr(b) if 32<=b<127 else '.' for b in chunk)}")

# 2. Search player_blob for any name containing "Bailey"
print(f"\n=== player_blob names containing 'Bailey' ===")
cur.execute("SELECT player_id, payload FROM player_blob")
found = []
for pid, payload in cur.fetchall():
    if b"Bailey" in payload or b"BAILEY" in payload or b"bailey" in payload:
        names = re.findall(b'[\x20-\x7e]{4,}', payload)
        print(f"  pid={pid}: {[n.decode() for n in names]}")
        found.append(pid)

# 3. Check team_blob for any team containing a modified player reference
print(f"\n=== team_blob sample (user team) ===")
# From step 3A: user chose a team via Win_ChooseTeam. targetTeamId is in UserPlayerSetupData.
# Let's check which team has player_id=1 in it
cur.execute("SELECT team_id, payload FROM team_blob LIMIT 5")
for tid, payload in cur.fetchall():
    print(f"  team_id={tid}: {len(payload)}B hex={payload[:60].hex()}...")

# 4. Check for user player with kit number / unusual ID
print(f"\n=== player_blob IDs > 175922 (new players) ===")
cur.execute("SELECT COUNT(*) FROM player_blob WHERE player_id > 175922")
print(f"  count: {cur.fetchone()[0]}")

# 5. Decode archive_blob at depth 5 and look for UserPlayer-like structures
print(f"\n=== archive_blob full decode (depth 5) ===")
fields = decode_message(raw, max_depth=5)
# Print only relevant branches (skip the huge competition list)
for f in fields:
    fn, wt, val, raw_b = f
    if wt == "message":
        print(f"f{fn} (message, {len(raw_b)}B):")
        # Check if any nested contains "BAILEY" or interesting strings
        if raw_b and (b"BAILEY" in raw_b or b"Bailey" in raw_b):
            print(f"  *** CONTAINS BAILEY ***")
            sub_lines = format_fields(val, 2)
            for line in sub_lines[:30]:
                print(line)
    elif wt == "string":
        if "CompName" not in str(val) and len(str(val)) < 100:
            print(f"f{fn} (string): {val!r}")
    elif wt == "varint":
        print(f"f{fn} (varint): {val}")

conn.close()
