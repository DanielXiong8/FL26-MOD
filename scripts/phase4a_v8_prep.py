# -*- coding: utf-8 -*-
"""
Phase 4A v8 prep:
1) Scan all TextAssets for hardcoded player count 52640 (0xCDA0)
2) Find unused pid < 175922 (not in Players, not in PlayerAppearanceTable keys, not in ClubPlayer)
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        assets[d.m_Name] = bytes(raw)

# 1) scan for 52640 as uint32 LE
target = struct.pack("<I", 52640)
print("=== Assets containing uint32 52640 ===")
for name, raw in assets.items():
    idx = raw.find(target)
    if idx >= 0:
        print(f"  {name}: {len(raw):,}B first@0x{idx:x}")

# also 52646 (appearance count) is known. 52641?
for val in [52641, 52646]:
    t = struct.pack("<I", val)
    hits = [n for n, r in assets.items() if t in r]
    print(f"uint32 {val} in: {hits[:10]}")

# 2) collect used pids
raw = assets['Players']
off = 8
ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
pids = set()
for i in range(pcnt):
    pid = struct.unpack_from("<I", raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
    off += 8 + 3 + 17 + 2 + 1 + 4
    pids.add(pid)

pa = assets['PlayerAppearanceTable']
nkeys = struct.unpack_from("<I", pa, 0)[0]
keys = set(struct.unpack_from("<I", pa, 4 + i*8)[0] for i in range(nkeys))

cp = assets['ClubPlayer']
n1 = struct.unpack_from("<I", cp, 0)[0]
cp_pids = set()
base = 4 + n1*8
j = 0
while base + j*17 + 17 <= len(cp):
    cp_pids.add(struct.unpack_from("<I", cp, base + j*17 + 4)[0])
    j += 1

print(f"\nplayers={len(pids)}, appearance keys={len(keys)}, clubplayer pids={len(cp_pids)}")

# find gaps < 175922
candidates = []
for p in range(200, 175922):
    if p not in pids and p not in keys and p not in cp_pids:
        candidates.append(p)
        if len(candidates) >= 20:
            break
print(f"first 20 fully-unused pids: {candidates}")

# how many players NOT in appearance table?
noapp = pids - keys
print(f"players without appearance entry: {len(noapp)} (sample: {sorted(noapp)[:10]})")
# how many appearance keys not players?
extrak = keys - pids
print(f"appearance keys not in Players: {len(extrak)} (sample: {sorted(extrak)[:10]})")
