# -*- coding: utf-8 -*-
"""
ClubPlayer: parse exact 17-byte records.
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

print(f"ClubPlayer: {len(raw)} bytes")

# Records are 17 bytes each, starting at some offset
# Team 20026 uint32 occurrences: 0x59c, then 0x2a054, 0x2a065, ... (17-byte spacing)
# Let's read 17-byte records starting from various offsets

# First, check what's at 0x59c (first occurrence)
print("Bytes at 0x59c:")
for i in range(0x59c - 8, 0x59c + 40, 17):
    rec = raw[i:i+17]
    hex_str = ' '.join(f'{b:02x}' for b in rec)
    print(f"  0x{i:x}: {hex_str}")

# Now check 0x2a054 area
print("\nBytes at 0x2a054 (17-byte records):")
for i in range(0x2a054 - 17, 0x2a054 + 17*5, 17):
    rec = raw[i:i+17]
    hex_str = ' '.join(f'{b:02x}' for b in rec)
    # Try to parse as: marker(4) + player_id(4) + f1(4) + f2(4) + f3(1)
    if len(rec) >= 17:
        marker = struct.unpack_from("<I", rec, 0)[0]
        pid = struct.unpack_from("<I", rec, 4)[0]
        f1 = struct.unpack_from("<I", rec, 8)[0]
        f2 = struct.unpack_from("<I", rec, 12)[0]
        f3 = rec[16]
        print(f"  0x{i:x}: marker=0x{marker:04x} pid={pid} f1={f1} f2={f2} f3={f3}")
        # Also check if team_id is at offset 0
        tid = struct.unpack_from("<I", rec, 0)[0]
        if 10000 <= tid <= 30000:
            print(f"    ^^ team_id={tid}")

# Let's find the actual start of the 17-byte record section
# by looking for the pattern backwards from 0x2a054
print("\n\nLooking for record section start...")
# Records at 0x2a054, 0x2a065, ... with 17-byte spacing
# Go backwards from 0x2a054 by 17 bytes each time
start_candidate = 0x2a054
for i in range(20):
    prev = start_candidate - 17 * i
    rec = raw[prev:prev+17]
    if len(rec) >= 8:
        val = struct.unpack_from("<I", rec, 0)[0]
        if val < 100 or val > 100000:
            print(f"  Possible section start at 0x{prev:x} (value={val})")
            break

# Actually, let's check if the section starts right after the header section
# Header: count(4) + team index
# vals[0] = 1862 = record count
# Then there's a team index section, then the actual records

# The header section has pairs of (team_id, player_count?)
# Let's count how many header entries there are
print("\n\nHeader section analysis:")
off = 4
entries = 0
while off + 8 <= len(raw):
    tid = struct.unpack_from("<I", raw, off)[0]
    pc = struct.unpack_from("<I", raw, off + 4)[0]
    if 10000 <= tid <= 40000 and 0 < pc < 100:
        entries += 1
        if entries <= 5 or entries % 100 == 0:
            print(f"  Entry {entries}: team={tid} count={pc} at offset 0x{off:x}")
        off += 8
    else:
        break

print(f"  Total header entries: {entries}")
print(f"  Header ends at offset: 0x{off:x}")
print(f"  Remaining bytes: {len(raw) - off}")
print(f"  If 17-byte records: {(len(raw) - off) / 17:.1f} records")

# Read first record at that offset
print(f"\nFirst 17-byte record at 0x{off:x}:")
rec = raw[off:off+17]
hex_str = ' '.join(f'{b:02x}' for b in rec)
print(f"  {hex_str}")
tid = struct.unpack_from("<I", rec, 0)[0]
pid = struct.unpack_from("<I", rec, 4)[0]
print(f"  As team+player: team={tid} player={pid}")
