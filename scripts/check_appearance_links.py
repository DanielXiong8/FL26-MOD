# -*- coding: utf-8 -*-
"""
Systematic check: which TextAssets contain player IDs and may need updating.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Known Arsenal player IDs
test_pids = [103346, 110947, 103281, 103643, 119091, 100389]

# Check all TextAssets for these PIDs
print("TextAssets containing known player IDs:")
print("=" * 60)

for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        raw = d.m_Script
        if isinstance(raw, str):
            raw_bytes = raw.encode('utf-8', errors='surrogateescape')
        else:
            raw_bytes = bytes(raw)
        
        found = []
        for pid in test_pids:
            if struct.pack("<I", pid) in raw_bytes:
                found.append(pid)
        
        if found:
            print(f"{name}: {len(raw_bytes):,}B - contains {len(found)} PIDs")
            for pid in found[:3]:
                idx = raw_bytes.find(struct.pack("<I", pid))
                print(f"  pid {pid} at 0x{idx:x}")

# Check StarPlayerAppearance
print("\n" + "=" * 60)
print("StarPlayerAppearance structure:")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'StarPlayerAppearance':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        # Try to parse
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"First uint32: {count}")
        # Show first 100 bytes
        print(f"Hex: {raw[:100].hex()}")
        break

# Check UserPlayerBaseInfo
print("\n" + "=" * 60)
print("UserPlayerBaseInfo:")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'UserPlayerBaseInfo':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        try:
            text = raw.decode('utf-8', errors='replace')
            lines = text.strip().split('\n')
            print(f"Lines: {len(lines)}")
            for line in lines[:10]:
                print(f"  {line}")
        except:
            print(f"Hex: {raw[:100].hex()}")
        break

# Check if there's a player -> appearance mapping table
print("\n" + "=" * 60)
print("Searching for appearance mapping tables:")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        name = obj.read().m_Name
        if any(w in name.lower() for w in ['appearance', 'avatar', 'face', 'look']):
            raw = obj.read().m_Script
            if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
            print(f"{name}: {len(raw):,}B")
