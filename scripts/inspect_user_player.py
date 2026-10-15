# -*- coding: utf-8 -*-
"""inspect_user_player.py — find and dump the UserPlayer record + archive blob."""
import sqlite3, os, sys

DB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
OUT = r"C:\FL26_Mod\recon\07_save"

conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

# 1. User player (player_id=1)
print("=== player_id=1 ===")
cur.execute("SELECT * FROM player_blob WHERE player_id=1")
row = cur.fetchone()
if row:
    print(f"data_scope={row[0]} player_id={row[1]} payload={len(row[2])}B")
    print(f"hex: {row[2].hex()}")
else:
    print("NOT FOUND")

# 2. Check for any player with data_scope != 0
print("\n=== distinct data_scope in player_blob ===")
cur.execute("SELECT DISTINCT data_scope, COUNT(*) FROM player_blob GROUP BY data_scope")
for r in cur.fetchall():
    print(f"  scope={r[0]}: {r[1]} rows")

# 3. Archive blob
print("\n=== archive_blob ===")
cur.execute("SELECT * FROM archive_blob")
row = cur.fetchone()
if row:
    print(f"id={row[0]} payload={len(row[1])}B")
    print(f"hex (first 512): {row[1][:512].hex()}")

# 4. Check for any players with very large payloads (user player might be bigger)
print("\n=== largest payloads ===")
cur.execute("SELECT player_id, LENGTH(payload) FROM player_blob ORDER BY LENGTH(payload) DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  player_id={r[0]}: {r[1]}B")

# 5. Check player_id range
print("\n=== player_id range ===")
cur.execute("SELECT MIN(player_id), MAX(player_id), COUNT(*) FROM player_blob")
r = cur.fetchone()
print(f"  min={r[0]} max={r[1]} count={r[2]}")

# 6. Dump player_id=1 payload to file for detailed analysis
cur.execute("SELECT payload FROM player_blob WHERE player_id=1")
row1 = cur.fetchone()
if row1:
    out_path = os.path.join(OUT, "user_player_blob.bin")
    with open(out_path, "wb") as f:
        f.write(row1[0])
    print(f"\n-> {out_path} ({len(row1[0])}B)")

# 7. Dump archive blob
cur.execute("SELECT payload FROM archive_blob WHERE id=1")
row = cur.fetchone()
if row:
    out_path = os.path.join(OUT, "archive_blob.bin")
    with open(out_path, "wb") as f:
        f.write(row[1])
    print(f"-> {out_path} ({len(row[1])}B)")

conn.close()
print("\ndone")
