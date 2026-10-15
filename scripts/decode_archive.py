# -*- coding: utf-8 -*-
"""decode_archive.py — full archive_blob decode focusing on UserPlayer + team structure."""
import sqlite3, sys, os
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields, read_varint

DB = r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
OUT = r"C:\FL26_Mod\recon\07_save"

conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()
cur.execute("SELECT payload FROM archive_blob WHERE id=1")
raw = cur.fetchone()[0]

# Full decode at max depth
fields = decode_message(raw, max_depth=6)
lines = format_fields(fields)

output = os.path.join(OUT, "archive_blob_decoded.txt")
with open(output, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"-> {output} ({len(lines)} lines)")

# Also dump just f2 (UserPlayer) and f5 (team info)
for fld in fields:
    fn, wt, val, raw_b = fld
    if fn in (2, 4, 5, 7, 8, 9) and wt == "message":
        print(f"\n=== archive_blob f{fn} ({len(raw_b)}B) ===")
        sub = decode_message(raw_b, max_depth=5)
        for line in format_fields(sub, 1):
            print(line)
    elif fn in (2, 4, 7, 9) and wt != "message":
        print(f"\narchive_blob f{fn} ({wt}): {val}")

conn.close()
