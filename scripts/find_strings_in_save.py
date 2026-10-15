# -*- coding: utf-8 -*-
"""find_strings_in_save.py — search for strings/names in all DB tables/blobs."""
import sqlite3, os, sys

DB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

# Search archive_blob for all readable ASCII/UTF-8 strings (>=3 chars)
cur.execute("SELECT payload FROM archive_blob WHERE id=1")
raw = cur.fetchone()[0]

print(f"=== STRINGS IN archive_blob ({len(raw)}B) ===")
import re
# Find UTF-8 printable runs >= 3 chars
matches = re.finditer(b'[\x20-\x7e]{3,}', raw)
for m in matches:
    print(f"  @0x{m.start():04x} [{m.end()-m.start()}ch]: {m.group().decode('ascii')}")

# Also scan player_blob for any non-default names
print("\n=== SAMPLE NAMES IN player_blob ===")
cur.execute("SELECT player_id, payload FROM player_blob LIMIT 20")
for pid, payload in cur.fetchall():
    # look for string field
    str_matches = list(re.finditer(b'[\x20-\x7e]{4,}', payload))
    strs = [m.group().decode('ascii', errors='replace') for m in str_matches]
    print(f"  pid={pid:<6}: {strs}")

# Check thumbnail DB
thumb_db = r"C:\FL26_Mod\saves\working\Common\PlayerCareerThumbnail.db"
if os.path.exists(thumb_db):
    print(f"\n=== PlayerCareerThumbnail.db ===")
    tc = sqlite3.connect(f"file:{thumb_db}?mode=ro&immutable=1", uri=True)
    tcur = tc.cursor()
    tcur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for t in tcur.fetchall():
        print(f"  table: {t[0]}")
        tcur.execute(f"SELECT * FROM [{t[0]}]")
        for r in tcur.fetchall():
            print(f"    row: {r}")
    tc.close()

conn.close()
