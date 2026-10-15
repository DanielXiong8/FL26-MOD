# -*- coding: utf-8 -*-
"""
Check why London Red bench disappeared in v8.
Examine ClubPlayer reading mechanism in Game:
1) How does game know where each team's players start in sec2?
   - Is it offset-based: offset = sum(cnt for previous teams in sec1)?
   - OR does sec1 have explicit offsets?
   - OR does it do a binary search / linear scan on sec2?
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read(check_read=False).m_Name == 'ClubPlayer':
        raw = obj.read(check_read=False).m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)

n1 = struct.unpack_from("<I", raw, 0)[0]
sec1 = [struct.unpack_from("<II", raw, 4 + i*8) for i in range(n1)]
base = 4 + n1*8
n2 = (len(raw) - base) // 17

print(f"sec1 teams: {n1}, sec2 records: {n2}")

# Check the order of team_ids in sec1 vs sec2
sec1_teams = [t[0] for t in sec1]

# Get the first occurrence of each team in sec2
sec2_team_order = []
last_t = None
for i in range(n2):
    t = struct.unpack_from("<I", raw, base + i*17)[0]
    if t != last_t:
        sec2_team_order.append(t)
        last_t = t

print(f"Distinct teams in sec2 in physical order: {len(sec2_team_order)}")
print(f"Is sec1 team order identical to sec2 team order? {sec1_teams == sec2_team_order}")

# If not identical, why?
if sec1_teams != sec2_team_order:
    print("Sec1 is sorted by team_id? ", sec1_teams == sorted(sec1_teams))
    print("Sec2 is sorted by team_id? ", sec2_team_order == sorted(sec2_team_order))
    
    # Check if sec1 is an INDEX sorted by team_id for binary search!
    # And if so, how does sec1 point to sec2?
    print("\nCheck sec1 entries around team 20030:")
    for i, (tid, cnt) in enumerate(sec1):
        if tid == 20030:
            print(f"  sec1[{i}]: team_id={tid}, val2={cnt}")

# Let's check what the second uint32 in sec1 ACTUALLY is!
# Is it count, or is it an offset/index into sec2?
print("\nComparing sec1 val2 with actual team counts in sec2:")
actual_counts = {}
for i in range(n2):
    t = struct.unpack_from("<I", raw, base + i*17)[0]
    actual_counts[t] = actual_counts.get(t, 0) + 1

matches = sum(1 for tid, v2 in sec1 if actual_counts.get(tid, 0) == v2)
print(f"sec1 val2 == actual count in sec2: {matches} / {len(sec1)}")

# Check cumulative sum of counts vs physical start index!
cumsum = 0
aligned_count = 0
for tid, cnt in sec1:
    # find first occurrence in sec2
    first_idx = next((i for i in range(n2) if struct.unpack_from("<I", raw, base + i*17)[0] == tid), None)
    if first_idx == cumsum:
        aligned_count += 1
    cumsum += cnt

print(f"sec1 cumulative sum matches physical sec2 start index: {aligned_count} / {len(sec1)}")
