# -*- coding: utf-8 -*-
"""
1) Which TextAssets contain known pids (find secondary per-player tables that may hold birthdate/foot info)
2) PlayerAppearanceTable key structure: are all keys = player pids?
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

arsenal_pid = 103346   # Ralla
t = struct.pack("<I", arsenal_pid)
print(f"=== TextAssets containing pid {arsenal_pid} (Ralla) ===")
hits = []
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)
        idx = raw.find(t)
        if idx >= 0:
            hits.append((d.m_Name, len(raw), idx))
for name, size, idx in hits:
    print(f"  {name}: {size:,}B  first@0x{idx:x}")

# PlayerAppearanceTable keys
print("\n=== PlayerAppearanceTable keys ===")
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', errors='surrogateescape')
            raw = bytes(raw)
            n = struct.unpack_from("<I", raw, 0)[0]
            print(f"entries: {n}")
            keys = []
            offs = []
            for i in range(n):
                k, o = struct.unpack_from("<II", raw, 4 + i*8)
                keys.append(k); offs.append(o)
            print(f"first 5 keys: {keys[:5]}  offs: {offs[:5]}")
            print(f"last 5 keys: {keys[-5:]}  offs: {offs[-5:]}")
            print(f"keys sorted: {keys == sorted(keys)}")
            print(f"key min/max: {min(keys)}/{max(keys)}")
            # is 103346 a key?
            print(f"103346 in keys: {103346 in keys}")
            if 103346 in keys:
                i = keys.index(103346)
                print(f"  -> entry idx {i}, offset 0x{offs[i]:x}")
                # dump the appearance record at that offset
                o = offs[i]
                print(f"  record hex (32B): {raw[o:o+32].hex()}")
            # check a couple more arsenal pids
            for p in [110947, 103281, 103643, 119091, 100389]:
                print(f"  {p} in keys: {p in keys}")
            # do keys look like pids? sample some Players pids
            break
