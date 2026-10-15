# -*- coding: utf-8 -*-
"""
ClubPlayer structure - look at repeating pattern around team 20026.
Team 20026 found at indices 358, 43028, 43045, 43062, 43079 (spacing=17)
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
vals = []
for i in range((len(raw) - 4) // 4):
    vals.append(struct.unpack_from("<I", raw, 4 + i * 4)[0])

# Team 20026 appears at indices 358, 43028, 43045, 43062, 43079
# Spacing is 17. Let's check if each "record" is 17 uint32 values.
# Index 358 context
print("Context around index 358 (first team 20026):")
for i in range(340, 400):
    print(f"  [{i:5d}] = {vals[i]:>10d} (0x{vals[i]:08x})")

print("\n\nContext around index 43028 (team 20026 area):")
for i in range(43020, 43100):
    print(f"  [{i:5d}] = {vals[i]:>10d} (0x{vals[i]:08x})")
