# -*- coding: utf-8 -*-
"""
ClubPlayer structure: analyze as uint32 array with known values.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

count = struct.unpack_from("<I", raw, 0)[0]
total_u32 = (len(raw) - 4) // 4
print(f"ClubPlayer: {len(raw)} bytes")
print(f"Count: {count}")
print(f"Total uint32 values after count: {total_u32}")
print(f"Values per record: {total_u32 / count:.1f}")

# Read all uint32 values
vals = []
for i in range(total_u32):
    vals.append(struct.unpack_from("<I", raw, 4 + i * 4)[0])

# Known: pid 100242 should be in ClubPlayer (team 20026 from MasterLeaguePlayer)
# pid 100373 (Reno) should also be there
# team 20026 should be there
known_pids = {100242, 100373, 111024, 103727}
known_teams = {20026, 20027, 20051, 20044}

print(f"\nSearching for known player IDs in uint32 stream...")
for pid in known_pids:
    indices = [i for i, v in enumerate(vals) if v == pid]
    if indices:
        print(f"  pid {pid}: found at indices {indices[:5]}")
    else:
        print(f"  pid {pid}: NOT FOUND")

print(f"\nSearching for known team IDs...")
for tid in known_teams:
    indices = [i for i, v in enumerate(vals) if v == tid]
    if indices:
        print(f"  team {tid}: found at indices {indices[:5]}")
    else:
        print(f"  team {tid}: NOT FOUND")

# Show value distribution
print(f"\nValue distribution:")
from collections import Counter
c = Counter(vals)
print(f"  Most common values: {c.most_common(10)}")
print(f"  Values < 100: {sum(1 for v in vals if v < 100)}")
print(f"  Values 100-1000: {sum(1 for v in vals if 100 <= v < 1000)}")
print(f"  Values 10000-20000: {sum(1 for v in vals if 10000 <= v < 20000)}")
print(f"  Values 20000-30000: {sum(1 for v in vals if 20000 <= v < 30000)}")
print(f"  Values 100000-180000: {sum(1 for v in vals if 100000 <= v < 180000)}")

# Maybe it's: team_count(4) + [team_id(4) + player_count(4) + player_ids...]
print(f"\nTrying structure: team_count + [team_id + player_count + pids...]")
off = 4
team_count = struct.unpack_from("<I", raw, off)[0]
print(f"If offset 4 = team_count: {team_count}")

# Actually, first uint32 IS 1862. If it's player record count:
# 1862 * 432.7 = too many bytes per record
# Let's try: first = total teams?
# vals[0] = 1862
# vals[1] = 150, vals[2] = 19, vals[3] = 151, vals[4] = 19
# This looks like: team_id=150, player_id=19, team_id=151, player_id=19
# If each record = 2 uint32 (team_id + player_id), then 1862 records = 3724 uint32
# But we have 201412 uint32 total, so 201412/1862 = 108.2 per record

# Maybe each record is: team_id(1) + player_count(1) + player_ids(N)
# Let's check: vals[0]=1862 could be total players
# Then vals[1]=150 = team_id
# vals[2]=19 = player_count for team 150
# Then next 19 values are player_ids
print(f"\nTrying structure: total_players(4) + [team_id(4) + count(4) + pids(count*4)]")
total = vals[0]  # 1862
print(f"Total players declared: {total}")

off_idx = 1
teams_parsed = 0
players_parsed = 0
team_data = []
try:
    while off_idx < len(vals) and players_parsed < total:
        team_id = vals[off_idx]; off_idx += 1
        pcount = vals[off_idx]; off_idx += 1
        pids = vals[off_idx:off_idx+pcount]; off_idx += pcount
        team_data.append((team_id, pids))
        players_parsed += len(pids)
        teams_parsed += 1
        if teams_parsed <= 5:
            print(f"  Team {team_id}: {pcount} players -> {pids[:5]}{'...' if pcount > 5 else ''}")

    print(f"\nParsed {teams_parsed} teams, {players_parsed} players")
    print(f"Consumed uint32 values: {off_idx} / {len(vals)}")

    # Check known teams
    for tid, pids in team_data:
        if tid == 20026:
            print(f"\nTeam 20026: {len(pids)} players -> {pids}")
        if tid == 20044:
            print(f"Team 20044: {len(pids)} players -> {pids[:10]}...")
        if tid == 20051:
            print(f"Team 20051: {len(pids)} players -> {pids}")

except Exception as e:
    print(f"Parse error: {e}")
