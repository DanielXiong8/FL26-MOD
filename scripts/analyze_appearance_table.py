# -*- coding: utf-8 -*-
"""
Analyze PlayerAppearanceTable structure and check if new player needs entry.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        
        print(f"PlayerAppearanceTable: {len(raw)} bytes")
        
        # First uint32: 52646
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"First uint32: {count}")
        
        # Second uint32: 11
        rec_size = struct.unpack_from("<I", raw, 4)[0]
        print(f"Second uint32 (record size?): {rec_size}")
        
        # Check if it's an array indexed by player ID
        # If max ID is ~175922, and we have 1.5MB...
        # 175923 * 8 = 1,407,384 bytes — close to our 1,533,164
        # So maybe: header(8) + records of 8 bytes each
        
        # Let's check: (1533164 - 8) / 8 = 191644.5
        # Not integer. Let's try: header(8) + count * rec_size
        # 52646 * rec_size = 1533164 - 8
        # rec_size = 1533156 / 52646 = 29.12...
        # Not integer either.
        
        # Maybe: header(8) + some structure
        # Let's look at the pattern
        print(f"\nFirst 10 uint32 values:")
        for i in range(10):
            val = struct.unpack_from("<I", raw, 8 + i*4)[0]
            print(f"  [{i}] {val} (0x{val:08x})")
        
        # Check if it's pairs of (id, offset)
        print(f"\nAs (id, offset) pairs:")
        for i in range(5):
            id_val = struct.unpack_from("<I", raw, 8 + i*8)[0]
            off_val = struct.unpack_from("<I", raw, 8 + i*8 + 4)[0]
            print(f"  [{i}] id={id_val} offset={off_val}")
        
        # Check if it's (id, something) where id is player ID
        # If player IDs are 100000-180000, and we have ~52646 records...
        # Maybe each record is 29 bytes? Or variable length?
        
        # Let's check if the first uint32 (52646) is the count and records are fixed size
        # 52646 * 29 = 1526734, plus 8 header = 1526742
        # But actual is 1533164, difference = 6422
        # 6422 / 52646 = 0.122 — not helpful
        
        # Try: maybe it's a hash table or indexed array
        # If we treat it as uint32 array:
        total_u32 = (len(raw) - 8) // 4
        print(f"\nTotal uint32 after header: {total_u32}")
        
        # Check if player IDs are stored as keys
        # Known Arsenal player: pid 103346 (Ralla)
        target = struct.pack("<I", 103346)
        idx = raw.find(target)
        if idx >= 0:
            print(f"\npid 103346 found at offset 0x{idx:x}")
            # Show context
            start = max(0, idx - 16)
            end = min(len(raw), idx + 48)
            for i in range(start, end, 16):
                hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
                print(f"  {i:6x}: {hex_str}")
        
        # Check if our new player 180001 would be in range
        print(f"\nIf indexed by player ID (8 bytes/entry):")
        max_id = (len(raw) - 8) // 8
        print(f"  Max ID: {max_id}")
        print(f"  Our player 180001 < {max_id}: {180001 < max_id}")
        break
