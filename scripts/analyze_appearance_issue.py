# -*- coding: utf-8 -*-
"""
Analyze PlayerAppearanceTable structure and understand why face models break.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Load PlayerAppearanceTable
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        
        print("PlayerAppearanceTable Deep Analysis:")
        print(f"Size: {len(raw)} bytes")
        
        # Header: count(4) + ?(4)
        count = struct.unpack_from("<I", raw, 0)[0]
        second = struct.unpack_from("<I", raw, 4)[0]
        print(f"Header: count={count}, second={second}")
        
        # Check if it's a hash map: player_id -> appearance_data_offset
        # Or an array indexed by player_id
        
        # Let's look for known player IDs in the table
        # Arsenal players: 103346, 110947, 103281, 103643, 119091
        known_pids = [103346, 110947, 103281, 103643, 119091, 100389]
        
        print(f"\nSearching for known player IDs in raw data:")
        for pid in known_pids:
            # Search as uint32 LE
            target = struct.pack("<I", pid)
            idx = raw.find(target)
            if idx >= 0:
                print(f"  pid {pid}: found at offset 0x{idx:x}")
                # Show context
                start = max(0, idx - 8)
                end = min(len(raw), idx + 24)
                hex_str = ' '.join(f'{raw[i]:02x}' for i in range(start, end))
                print(f"    context: {hex_str}")
            else:
                print(f"  pid {pid}: NOT FOUND")
        
        # Check if table is indexed by player_id
        # If player_id is used as index, then entry size = (len(raw) - 8) / max_id
        # Max known player ID is ~175922
        max_known_id = 175922
        entry_size = (len(raw) - 8) / max_known_id
        print(f"\nIf indexed by player_id (max={max_known_id}):")
        print(f"  Entry size: {entry_size:.2f} bytes")
        
        # Check if entry size is 8 bytes
        if abs(entry_size - 8.0) < 0.1:
            print("  -> Likely 8 bytes per entry (indexed by player_id)")
            # Read entry for pid 103346
            pid = 103346
            offset = 8 + pid * 8
            if offset + 8 <= len(raw):
                val1, val2 = struct.unpack_from("<II", raw, offset)
                print(f"  Entry for pid {pid}: val1={val1} (0x{val1:08x}) val2={val2} (0x{val2:08x})")
        
        # Check if entry size is 4 bytes
        if abs(entry_size - 4.0) < 0.1:
            print("  -> Likely 4 bytes per entry (indexed by player_id)")
            pid = 103346
            offset = 8 + pid * 4
            if offset + 4 <= len(raw):
                val = struct.unpack_from("<I", raw, offset)[0]
                print(f"  Entry for pid {pid}: {val} (0x{val:08x})")
        
        break

# Check avatar bundle for face meshes
print("\n" + "=" * 60)
print("Avatar bundle face meshes:")
print("=" * 60)

env2 = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
face_meshes = []
for obj in env2.objects:
    if obj.type.name == 'Mesh':
        name = obj.read().m_Name
        if 'face' in name.lower():
            face_meshes.append(name)

print(f"Face meshes found: {len(face_meshes)}")
for name in face_meshes[:10]:
    print(f"  {name}")

# Check if there's a mapping from player_id to face_mesh
print("\n" + "=" * 60)
print("Checking for player_id -> face_mesh mapping:")
print("=" * 60)

# Look for TextAssets in avatar bundle that might contain mapping
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        name = obj.read().m_Name
        print(f"  TextAsset: {name}")
