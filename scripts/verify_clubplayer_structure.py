# -*- coding: utf-8 -*-
"""
Verify ClubPlayer Section 1 count vs Section 2 actual records.
Check if Section 2 is ordered by Section 1 team order.
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

# Parse Section 1
count = struct.unpack_from("<I", raw, 0)[0]
sec1 = []
off = 4
for i in range(count):
    tid = struct.unpack_from("<I", raw, off)[0]
    cnt = struct.unpack_from("<I", raw, off + 4)[0]
    sec1.append((tid, cnt, i))  # i = order in section 1
    off += 8

# Parse Section 2
sec2 = []
while off + 17 <= len(raw):
    tid = struct.unpack_from("<I", raw, off)[0]
    pid = struct.unpack_from("<I", raw, off + 4)[0]
    f1 = struct.unpack_from("<I", raw, off + 8)[0]
    f2 = struct.unpack_from("<I", raw, off + 12)[0]
    f3 = raw[off + 16]
    sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": f3, "_offset": off})
    off += 17

print(f"Section 1: {len(sec1)} teams")
print(f"Section 2: {len(sec2)} records")

# Check if Section 1 count sum == Section 2 count
total_sec1 = sum(cnt for _, cnt, _ in sec1)
print(f"\nSection 1 count sum: {total_sec1}")
print(f"Section 2 actual count: {len(sec2)}")
print(f"Match: {total_sec1 == len(sec2)}")

# Check if Section 2 is ordered by Section 1 team order
print(f"\nChecking if Section 2 follows Section 1 order:")
sec1_order = [tid for tid, _, _ in sec1]
sec2_order = [r["team_id"] for r in sec2]

# Find team 20030 in section 1
for tid, cnt, idx in sec1:
    if tid == 20030:
        print(f"Team 20030 in Section 1: index={idx}, count={cnt}")
        # Find where team 20030 records start in Section 2
        # If ordered, it should start at sum of all previous counts
        expected_start = sum(c for _, c, i in sec1 if i < idx)
        print(f"Expected Section 2 start index: {expected_start}")
        # Check actual records
        actual_records = [r for r in sec2 if r["team_id"] == 20030]
        print(f"Actual Section 2 records for team 20030: {len(actual_records)}")
        if actual_records:
            print(f"First record offset: 0x{actual_records[0]['_offset']:x}")
            print(f"Last record offset: 0x{actual_records[-1]['_offset']:x}")
        break

# Check if Section 2 is grouped by team_id
print(f"\nSection 2 team_id transitions:")
prev_tid = None
transitions = []
for i, r in enumerate(sec2):
    if r["team_id"] != prev_tid:
        transitions.append((i, r["team_id"]))
        prev_tid = r["team_id"]
print(f"Total transitions: {len(transitions)}")
print(f"First 10 transitions: {transitions[:10]}")

# Check if transitions match Section 1 order
print(f"\nDo transitions match Section 1 order?")
match = True
for i, (sec2_idx, tid) in enumerate(transitions[:20]):
    if i < len(sec1_order) and sec1_order[i] != tid:
        print(f"  Mismatch at {i}: Section 1 has {sec1_order[i]}, Section 2 has {tid}")
        match = False
        break
if match:
    print("  Yes, Section 2 follows Section 1 order")
