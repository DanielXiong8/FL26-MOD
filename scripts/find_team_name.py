# -*- coding: utf-8 -*-
"""Find team 20026 name and League structure."""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Teams table
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Teams':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        print(f"Teams: {len(raw)} bytes")
        print(f"Magic: {raw[:8].hex()} = {raw[:8].decode('ascii', errors='replace')}")

        # Search for team 20026 as uint32
        target = struct.pack("<I", 20026)
        idx = raw.find(target)
        if idx >= 0:
            print(f"\nTeam 20026 at offset 0x{idx:x}:")
            # Show surrounding bytes
            start = max(0, idx - 16)
            end = min(len(raw), idx + 80)
            for i in range(start, end, 16):
                hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
                print(f"  {i:6x}: {hex_str}")
            # Try to decode name after the ID
            # Usually: id(4) + name_len(2) + name(utf16)
            try:
                nlen = struct.unpack_from("<H", raw, idx+4)[0]
                if 0 < nlen < 50:
                    name = raw[idx+6:idx+6+nlen*2].decode('utf-16-le', errors='replace')
                    print(f"  Possible name (len={nlen}): {name}")
            except:
                pass
            # Try: id(4) + name_len(4) + name(utf16)
            try:
                nlen = struct.unpack_from("<I", raw, idx+4)[0]
                if 0 < nlen < 50:
                    name = raw[idx+8:idx+8+nlen*2].decode('utf-16-le', errors='replace')
                    print(f"  Alt name (len={nlen}): {name}")
            except:
                pass
        break

# League_new table
print("\n" + "=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'League_new':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        print(f"League_new: {len(raw)} bytes")
        print(f"First 64 bytes: {raw[:64].hex()}")
        # Check if it's CSV
        try:
            text = raw.decode('utf-8', errors='replace')
            lines = text.strip().split('\n')
            print(f"Lines: {len(lines)}")
            for line in lines[:10]:
                print(f"  {line}")
        except:
            print("Not plain text")
        break

# Also check team names in CompName_EnglishLeagueA
print("\n" + "=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'CompName_EnglishLeagueA':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        print(f"CompName_EnglishLeagueA: {len(raw)} bytes")
        try:
            text = raw.decode('utf-8', errors='replace')
            lines = text.strip().split('\n')
            print(f"Lines: {len(lines)}")
            for line in lines[:30]:
                print(f"  {line}")
        except:
            print(f"Not plain text, first 100 bytes: {raw[:100].hex()}")
        break
