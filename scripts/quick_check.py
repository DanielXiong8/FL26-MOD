# -*- coding: utf-8 -*-
"""Quick check: FaceTemplate.csv and PlayerAppearanceTable for new player."""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Check FaceTemplate.csv
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'FaceTemplate.csv':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        text = raw.decode('utf-8', errors='replace')
        lines = text.strip().split('\n')
        print(f'FaceTemplate.csv: {len(lines)} lines')
        for line in lines[:5]:
            print(f'  {line}')
        break

# Check PlayerAppearanceTable for pid 180001
print('\nChecking pid 180001 in PlayerAppearanceTable:')
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        target = struct.pack('<I', 180001)
        idx = raw.find(target)
        print(f'  Found: {idx >= 0}')
        if idx >= 0:
            print(f'  Offset: 0x{idx:x}')
        break

# Check if our new player is in any other tables
print('\nChecking pid 180001 in all TextAssets:')
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        name = obj.read().m_Name
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        if struct.pack('<I', 180001) in raw:
            print(f'  {name}: FOUND')
