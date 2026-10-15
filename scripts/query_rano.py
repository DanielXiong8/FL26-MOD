# -*- coding: utf-8 -*-
"""Investigate: who is 'Rano'? Which team? And what's team 152's real identity?"""
import csv

BASE = r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon"

players = {r["player_id"]: r for r in csv.DictReader(open(BASE + r"\03_player\player_registry_candidates.csv", encoding="utf-8-sig"))}
clubs = list(csv.DictReader(open(BASE + r"\04_team\clubplayer_registry.csv", encoding="utf-8-sig")))
teams = {r["id"]: r for r in csv.DictReader(open(BASE + r"\04_team\team_registry_candidates.csv", encoding="utf-8-sig"))}

# 1. find Rano in players
rano = [p for p in players.values() if p["name"].lower() == "rano"]
print(f"players named 'Rano': {[(p['player_id'], p['name']) for p in rano]}")
# fuzzy
rano2 = [p for p in players.values() if "rano" in p["name"].lower()]
print(f"players containing 'rano': {[(p['player_id'], p['name']) for p in rano2][:10]}")

# 2. Rano's club(s)
for p in rano:
    pid = p["player_id"]
    memberships = [c for c in clubs if c["player_id"] == pid]
    print(f"  pid={pid} memberships: {[(m['team_id'], m['slot_index'], m['jersey'], m['role_byte13']) for m in memberships]}")
    for m in memberships:
        t = teams.get(m["team_id"], {})
        print(f"    team {m['team_id']}: {t.get('name')} ({t.get('classification')})")

# 3. team 152 identity check
t152 = teams.get("152", {})
print(f"\nteam 152: {dict(t152)}")

# 4. all teams with 'Fulham' in name
ful = [t for t in teams.values() if "fulham" in (t.get("name","") + t.get("realname","")).lower()]
print(f"\nFulham teams: {[(t['id'], t['name'], t.get('realname','')) for t in ful]}")

# 5. team 152 first 12 slots with names
print("\nteam 152 slots 0..11:")
for c in [c for c in clubs if c["team_id"] == "152"][:12]:
    p = players.get(c["player_id"], {})
    print(f"  slot={c['slot_index']:>2} pid={c['player_id']:>7} name={p.get('name','?'):<18} #{c['jersey']:>2} role={c['role_byte13']}")
