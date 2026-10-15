# -*- coding: utf-8 -*-
"""Dump team 20030 original ClubPlayer sec2 records: f1 sequence + neighbor team blocks."""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
cp = None
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'ClubPlayer':
            raw = d.m_Script
            cp = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

n1 = struct.unpack_from("<I", cp, 0)[0]
sec1 = [struct.unpack_from("<II", cp, 4 + i*8) for i in range(n1)]
base = 4 + n1*8
sec2 = []
j = 0
while base + j*17 + 17 <= len(cp):
    tid, pid, f1, f2 = struct.unpack_from("<IIII", cp, base + j*17)
    sec2.append((tid, pid, f1, f2, cp[base + j*17 + 16]))
    j += 1

# team 20030 block
rows = [(i, r) for i, r in enumerate(sec2) if r[0] == 20030]
print(f"team 20030: {len(rows)} records, idx {rows[0][0]}..{rows[-1][0]}")
for i, r in rows:
    print(f"  [{i}] pid={r[1]:>7} f1={r[2]:>3} f2={r[3]:>5} f3={r[4]}")

# what team is at 2576 (where v6 wrongly inserted)?
print("\nteam block around idx 2576 (orig):")
for i in range(2570, 2582):
    print(f"  [{i}] team={sec2[i][0]} pid={sec2[i][1]} f1={sec2[i][2]}")

# team 10067 full
t10067 = [r for r in sec2 if r[0] == 10067]
print(f"\nteam 10067: {len(t10067)} records, sec1 says: {[c for t,c in sec1 if t==10067]}")

# teams adjacent to 20030 in physical order
i0 = rows[0][0]
print("\nphysical neighbors of 20030 block:")
print(f"  before: [{i0-1}] team={sec2[i0-1][0]} pid={sec2[i0-1][1]}")
i1 = rows[-1][0]
print(f"  after:  [{i1+1}] team={sec2[i1+1][0]} pid={sec2[i1+1][1]}")

# f1 duplicates check within 20030
f1s = [r[2] for _, r in rows]
print(f"\nf1 values: {sorted(f1s)}")
print(f"f1=1 already present: {1 in f1s}")
