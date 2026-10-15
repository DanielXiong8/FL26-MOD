# -*- coding: utf-8 -*-
import csv
from collections import Counter

rows = [r for r in csv.DictReader(open(r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon\04_team\clubplayer_registry.csv", encoding="utf-8-sig")) if r["team_id"] == "152"]
print(f"team 152 squad size: {len(rows)}")
print("role dist:", Counter(r["role_byte13"] for r in rows).most_common())
print()
print("first 35 slots:")
for r in rows[:35]:
    print(f"  slot={r['slot_index']:>3} pid={r['player_id']:>7} {r['player_name'][:22]:<22} #{r['jersey']:>2} role={r['role_byte13']}")
print()
print("jersey 1..11 (probable starters):")
for r in rows:
    if r["jersey"] in [str(i) for i in range(1, 12)]:
        print(f"  pid={r['player_id']:>7} {r['player_name'][:22]:<22} #{r['jersey']:>2} role={r['role_byte13']} slot={r['slot_index']}")
