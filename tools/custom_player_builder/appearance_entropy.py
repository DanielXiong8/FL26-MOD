# -*- coding: utf-8 -*-
"""
Track A-prep: Byte-level entropy analysis of all 52,646 appearance records.
Identifies which bytes in the 17B appearance data are variable (likely parameters)
vs constant (likely structure/flags).
"""
import struct, sys, io, math
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read(check_read=False).m_Name == 'PlayerAppearanceTable':
        raw = obj.read(check_read=False).m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)
        break

n = struct.unpack_from("<I", raw, 0)[0]
idx_entries = [struct.unpack_from("<II", raw, 4 + i*8) for i in range(n)]
data_start = 4 + n*8

print(f"Total appearance records: {n}")

# Extract all 17B data payloads
records = []
pids = []
for k, o in idx_entries:
    # Each record is 21B: pid(4) + data(17)
    # But are they all exactly 21B? Check by looking at consecutive offsets
    records.append(raw[o:o+21])
    pids.append(k)

# Verify record length consistency
sizes = set()
sorted_idx = sorted(idx_entries, key=lambda x: x[1])
for i in range(len(sorted_idx)-1):
    sizes.add(sorted_idx[i+1][1] - sorted_idx[i][1])
# Last record size = file_end - offset
sizes.add(len(raw) - sorted_idx[-1][1])
print(f"Record sizes found: {sorted(sizes)}")

if len(sizes) == 1 and list(sizes)[0] == 21:
    print("All records are exactly 21 bytes (4 pid + 17 data)")
else:
    print("WARNING: Variable record sizes detected!")

# Per-byte analysis (the 17 data bytes)
print("\n" + "="*80)
print("Per-byte value distribution (17 data bytes):")
print("="*80)

for byte_idx in range(17):
    vals = [r[4 + byte_idx] for r in records]
    cnt = Counter(vals)
    unique = len(cnt)
    most_common = cnt.most_common(5)
    
    # Calculate entropy
    total = len(vals)
    entropy = 0.0
    for v in cnt.values():
        p = v / total
        if p > 0:
            entropy -= p * math.log2(p)
    
    print(f"Byte {byte_idx:2d}: {unique:4d} unique, entropy={entropy:6.2f}, top5={most_common}")

# Special analysis: Ralla's record (our template)
ralla_idx = pids.index(103346)
ralla_data = records[ralla_idx][4:]
print(f"\nRalla (103346) appearance data: {ralla_data.hex()}")
print(f"As bytes: {[f'{b:3d}' for b in ralla_data]}")

# Check correlation between bytes
print("\n" + "="*80)
print("Checking if bytes 0-3 might be a uint16/uint32 (e.g., face template ID):")
print("="*80)
# bytes 0-1 as uint16
u16_01 = [struct.unpack_from("<H", r, 4)[0] for r in records]
cnt = Counter(u16_01)
print(f"Bytes[0:2] as uint16: {len(cnt)} unique, top10={cnt.most_common(10)}")

# bytes 2-3 as uint16
u16_23 = [struct.unpack_from("<H", r, 6)[0] for r in records]
cnt = Counter(u16_23)
print(f"Bytes[2:4] as uint16: {len(cnt)} unique, top10={cnt.most_common(10)}")
