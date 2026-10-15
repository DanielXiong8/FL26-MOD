# -*- coding: utf-8 -*-
"""
Analyze League_new and League_variant tables for team rosters.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# League_new
print("=" * 60)
print("League_new table")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'League_new':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        # Header: X\x00\x00\x00 = 88 (0x58) = number of leagues?
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"First uint32: {count}")
        
        # Show hex dump of first 100 bytes
        print("First 100 bytes:")
        for i in range(0, min(100, len(raw)), 16):
            hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, len(raw)-i)))
            ascii_str = ''.join(chr(raw[i+j]) if 32 <= raw[i+j] < 127 else '.' for j in range(min(16, len(raw)-i)))
            print(f"  {i:4x}: {hex_str:<48s} {ascii_str}")
        
        # Find team 20030 in League_new
        target = struct.pack("<I", 20030)
        idx = raw.find(target)
        if idx >= 0:
            print(f"\nTeam 20030 at offset 0x{idx:x}")
            # Show context
            start = max(0, idx - 32)
            end = min(len(raw), idx + 100)
            for i in range(start, end, 16):
                hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
                print(f"  {i:4x}: {hex_str}")
        break

# League_variant
print("\n" + "=" * 60)
print("League_variant tables")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'League_variant':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        
        # Find team 20030
        target = struct.pack("<I", 20030)
        idx = raw.find(target)
        if idx >= 0:
            print(f"Team 20030 at offset 0x{idx:x}")
            start = max(0, idx - 32)
            end = min(len(raw), idx + 100)
            for i in range(start, end, 16):
                hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
                print(f"  {i:4x}: {hex_str}")
        break

# Check specialEditionPlayers
print("\n" + "=" * 60)
print("specialEditionPlayers")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'specialEditionPlayers':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        print(f"Hex: {raw[:64].hex()}")
        # Check if it's a list of player IDs
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"Count: {count}")
        pids = []
        for i in range(count):
            pid = struct.unpack_from("<I", raw, 4 + i*4)[0]
            pids.append(pid)
        print(f"Player IDs: {pids}")
        break

# Check topTierClubs
print("\n" + "=" * 60)
print("topTierClubs")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'topTierClubs':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"Size: {len(raw)} bytes")
        print(f"Hex: {raw.hex()}")
        # Parse as uint32 list
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"Count: {count}")
        tids = []
        for i in range(count):
            tid = struct.unpack_from("<I", raw, 4 + i*4)[0]
            tids.append(tid)
        print(f"Team IDs: {tids}")
        print(f"Team 20030 in topTierClubs: {20030 in tids}")
        break
