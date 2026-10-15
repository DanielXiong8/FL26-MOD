# -*- coding: utf-8 -*-
"""analyze_save_db.py — read-only SQLite schema + data inventory."""
import sqlite3, json, os, sys

DB = sys.argv[1] if len(sys.argv) > 1 else r"C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db"
OUT_DIR = r"C:\FL26_Mod\recon\07_save"
os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

report = []
report.append(f"# SQLite Schema — {os.path.basename(DB)}")
report.append(f"File: {DB}")
report.append(f"Size: {os.path.getsize(DB):,} bytes\n")

# Tables
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
report.append(f"## Tables ({len(tables)})\n")

inventory_rows = []

for name, sql in tables:
    report.append(f"### {name}")
    report.append(f"```sql\n{sql}\n```")
    
    cur.execute(f"SELECT COUNT(*) FROM [{name}]")
    count = cur.fetchone()[0]
    report.append(f"Rows: **{count}**\n")
    
    cur.execute(f"PRAGMA table_info([{name}])")
    cols = cur.fetchall()
    report.append("| # | Column | Type | PK | NotNull | Default |")
    report.append("|---|--------|------|----|---------|---------|")
    for c in cols:
        report.append(f"| {c[0]} | {c[1]} | {c[2]} | {c[5]} | {c[3]} | {c[4]} |")
    report.append("")
    
    inventory_rows.append({
        "table": name,
        "rows": count,
        "columns": [{"name": c[1], "type": c[2], "pk": c[5]} for c in cols]
    })
    
    # Show first 3 rows (limited columns for blob inspection)
    cur.execute(f"SELECT * FROM [{name}] LIMIT 3")
    rows = cur.fetchall()
    if rows:
        report.append("Sample data (first 3 rows, blobs as hex prefix):\n")
        col_names = [c[1] for c in cols]
        for i, row in enumerate(rows):
            report.append(f"Row {i}:")
            for j, val in enumerate(row):
                if isinstance(val, bytes):
                    hex_str = val[:64].hex() if len(val) > 64 else val.hex()
                    report.append(f"  {col_names[j]}: BLOB[{len(val)}B] = {hex_str}{'...' if len(val)>64 else ''}")
                elif isinstance(val, str) and len(val) > 200:
                    report.append(f"  {col_names[j]}: STR[{len(val)}ch] = {val[:100]}...")
                else:
                    report.append(f"  {col_names[j]}: {val}")
            report.append("")

# Indexes
cur.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name")
indexes = cur.fetchall()
if indexes:
    report.append(f"\n## Indexes ({len(indexes)})\n")
    for name, tbl, sql in indexes:
        report.append(f"- `{name}` on `{tbl}`: {sql}")

# Write reports
schema_path = os.path.join(OUT_DIR, "sqlite_schema.md")
with open(schema_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print(f"-> {schema_path}")

inv_path = os.path.join(OUT_DIR, "sqlite_inventory.json")
with open(inv_path, "w", encoding="utf-8") as f:
    json.dump(inventory_rows, f, indent=2, ensure_ascii=False)
print(f"-> {inv_path}")

# CSV
import csv
csv_path = os.path.join(OUT_DIR, "sqlite_inventory.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["table", "column", "type", "pk", "rows_in_table"])
    for t in inventory_rows:
        for c in t["columns"]:
            w.writerow([t["table"], c["name"], c["type"], c["pk"], t["rows"]])
print(f"-> {csv_path}")

conn.close()
print("done")
