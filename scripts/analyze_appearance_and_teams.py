# -*- coding: utf-8 -*-
"""
Deep-dive the data structures for team rosters and appearance tables.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

print("=" * 60)
print("1. Teams Table - structure and team 20030 entry")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Teams':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        # It's CSV: id,name,flag,nameAbbr,Nation,City_Name,classification,realname,realnameAbbr,Secondary classification,staticRating
        text = raw.decode('utf-8', errors='replace')
        for line in text.strip().split('\n'):
            if line.startswith('20030,'):
                print(f"  Team 20030 CSV: {line.strip()}")
        break

print("\n" + "=" * 60)
print("2. PlayerAppearanceTable - structure & entry format")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"  Size: {len(raw)} bytes")
        # Check header
        # First uint32: a6cd0000 = 52646 (little endian)
        header_count = struct.unpack_from("<I", raw, 0)[0]
        print(f"  First uint32: {header_count} (likely record count or ID max)")
        
        # Next: 0b000000 = 11 (record size?)
        rec_size = struct.unpack_from("<I", raw, 4)[0]
        print(f"  Next uint32: {rec_size} (bytes per record?)")
        
        # If 52646 records * 11 bytes = 579106 bytes... not 1.5MB
        # Maybe: header(8) + records of (id:4 + something:7) ?
        # Or record size is something else.
        # Let's assume record size = 12 bytes? 52646 * 12 = 631752
        # Let's check if size = 8 + count * rec_size
        calc_size = 8 + header_count * 12
        print(f"  Calc size (12B/record): {calc_size} vs actual: {len(raw)}")
        
        # Try parsing first few records assuming 12-byte records: id(4) + f1(4) + f2(4)
        print("  First 5 records (assuming 12B/record):")
        off = 8
        for i in range(5):
            rid = struct.unpack_from("<I", raw, off)[0]
            f1 = struct.unpack_from("<I", raw, off+4)[0]
            f2 = struct.unpack_from("<I", raw, off+8)[0]
            print(f"    [{i}] id={rid} f1={f1} f2={f2}")
            off += 12
        break

print("\n" + "=" * 60)
print("3. ClubPlayer Section 1 (Teams and player counts)")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"  Section 1 entries: {count}")
        # Find team 20030 in section 1
        off = 4
        for i in range(count):
            tid = struct.unpack_from("<I", raw, off)[0]
            cnt = struct.unpack_from("<I", raw, off+4)[0]
            if tid == 20030:
                print(f"  Team 20030 in Section 1: count={cnt} (index {i})")
            off += 8
        break

print("\n" + "=" * 60)
print("4. Check if players in Team 20030 (ClubPlayer Sec2) exist in AppearanceTable")
print("=" * 60)

# Load Players to get pids for team 20030
sec1 = []
sec2 = []
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        count = struct.unpack_from("<I", raw, 0)[0]
        off = 4
        for i in range(count):
            sec1.append((struct.unpack_from("<I", raw, off)[0], struct.unpack_from("<I", raw, off+4)[0]))
            off += 8
        while off + 17 <= len(raw):
            tid = struct.unpack_from("<I", raw, off)[0]
            pid = struct.unpack_from("<I", raw, off + 4)[0]
            f1 = struct.unpack_from("<I", raw, off + 8)[0]
            f2 = struct.unpack_from("<I", raw, off + 12)[0]
            f3 = raw[off + 16]
            sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": f3})
            off += 17
        break

team20030_pids = [r["player_id"] for r in sec2 if r["team_id"] == 20030]
print(f"  Team 20030 has {len(team20030_pids)} players in ClubPlayer Sec2")
print(f"  First 5 PIDs: {team20030_pids[:5]}")

# Check AppearanceTable raw size
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        # Check if size = 8 + max_id * 4 (simple array of uint32 offsets)
        max_possible_id = (len(raw) - 8) // 4
        print(f"  If AppearanceTable is uint32 array, max_id = {max_possible_id}")
        # Check first few values
        vals = struct.unpack_from("<5I", raw, 8)
        print(f"  First 5 uint32s after header: {vals}")
        # If max ID is ~175922, check size: 175923 * 4 = 703692 + 8 = 703700
        # But size is 1.5MB, so maybe 8 bytes per entry? 175923 * 8 = 1407384 + 8
        # 8 bytes per entry fits!
        rec_size = 8
        entries = (len(raw) - 8) // rec_size
        print(f"  If {rec_size} bytes/entry: {entries} entries")
        print(f"  This covers IDs up to {entries - 1} (or 0 to {entries-1})")
        print(f"  Our new player ID {180001} < {entries}: {180001 < entries}")
        break
