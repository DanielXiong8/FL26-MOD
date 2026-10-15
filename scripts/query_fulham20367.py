# -*- coding: utf-8 -*-
"""Real Fulham (20367) squad + does 'Rano' appear anywhere near it?"""
import csv

BASE = r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon"
players = {r["player_id"]: r for r in csv.DictReader(open(BASE + r"\03_player\player_registry_candidates.csv", encoding="utf-8-sig"))}
clubs = list(csv.DictReader(open(BASE + r"\04_team\clubplayer_registry.csv", encoding="utf-8-sig")))

squad = [c for c in clubs if c["team_id"] == "20367"]
print(f"Fulham (20367) squad size: {len(squad)}")
from collections import Counter
print("role dist:", Counter(c["role_byte13"] for c in squad).most_common())
print("\nslots 0..25:")
for c in squad[:26]:
    p = players.get(c["player_id"], {})
    nm = p.get("name", "?")
    print(f"  slot={c['slot_index']:>2} pid={c['player_id']:>7} {nm:<20} #{c['jersey']:>2} role={c['role_byte13']} nat={p.get('nation_index','?')}")

# search Rano-like across ALL players (starts with Ra)
ra = [p for p in players.values() if p["name"].lower().startswith("ran")]
print(f"\nplayers starting with 'Ran': {[(p['player_id'], p['name']) for p in ra][:15]}")
