# -*- coding: utf-8 -*-
"""
Analyze ClubPlayer binary format and League-related classes in dump.cs
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# ── ClubPlayer binary analysis ──
print("=" * 60)
print("ClubPlayer Binary Structure Analysis")
print("=" * 60)

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        print(f"Total size: {len(raw)} bytes")
        print(f"First 32 bytes hex: {raw[:32].hex()}")

        # Try to parse header
        off = 0
        val1 = struct.unpack_from("<I", raw, off)[0]; off += 4
        print(f"Offset 0: {val1} (0x{val1:x})")
        val2 = struct.unpack_from("<I", raw, off)[0]; off += 4
        print(f"Offset 4: {val2} (0x{val2:x})")
        val3 = struct.unpack_from("<I", raw, off)[0]; off += 4
        print(f"Offset 8: {val3} (0x{val3:x})")

        # If val1 is count, try record parsing
        # Look for pattern: player_id (4B) + team_id (4B) or similar
        print(f"\nFirst 200 bytes hex dump:")
        for i in range(0, min(200, len(raw)), 16):
            hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, len(raw)-i)))
            ascii_str = ''.join(chr(raw[i+j]) if 32 <= raw[i+j] < 127 else '.' for j in range(min(16, len(raw)-i)))
            print(f"  {i:6x}: {hex_str:<48s} {ascii_str}")

        # Try: count(4) then records of pid(4) + team_id(4) = 8 bytes
        count = val1
        if 0 < count < 200000 and len(raw) >= 8 + count * 8:
            print(f"\nTrying: count={count}, record=8 bytes (pid+team_id)")
            recs = []
            off = 8
            for i in range(min(count, 20)):
                pid = struct.unpack_from("<I", raw, off)[0]
                tid = struct.unpack_from("<I", raw, off+4)[0]
                recs.append((pid, tid))
                off += 8
            for pid, tid in recs:
                print(f"  pid={pid} team={tid}")

        # Try: count(4) then variable records
        # Look for player names in the binary
        print(f"\nSearching for known player names in ClubPlayer...")
        # We know pid=100373 is 'Reno' from modify_bundle.py
        # pid=100242 is in MasterLeaguePlayer team 20026
        # Search for 100242 as uint32 LE
        target = struct.pack("<I", 100242)
        idx = raw.find(target)
        if idx >= 0:
            print(f"Found pid 100242 at offset 0x{idx:x}")
            # Show surrounding bytes
            start = max(0, idx - 16)
            end = min(len(raw), idx + 32)
            print(f"Context (0x{start:x} - 0x{end:x}):")
            for i in range(start, end, 16):
                hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
                print(f"  {i:6x}: {hex_str}")

        target = struct.pack("<I", 100373)
        idx = raw.find(target)
        if idx >= 0:
            print(f"\nFound pid 100373 at offset 0x{idx:x}")

        # Search for team 20026
        target = struct.pack("<I", 20026)
        idx = raw.find(target)
        if idx >= 0:
            print(f"Found team 20026 at offset 0x{idx:x}")
        break

# ── dump.cs League analysis ──
print("\n" + "=" * 60)
print("dump.cs League-Related Classes")
print("=" * 60)

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\dump.cs', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Search for League-related classes/methods
league_keywords = [
    'LeaguePlayer', 'LeagueRoster', 'LeagueTeam', 'LeagueMatch',
    'MasterLeague', 'ClubPlayer', 'PlayerAppearance',
    'League.CreatePlayer', 'League.AddPlayer', 'League.GetPlayer',
    'League.Initialize', 'League.Setup',
]

for kw in league_keywords:
    idx = content.find(kw)
    if idx >= 0:
        # Show context
        start = max(0, idx - 100)
        end = min(len(content), idx + 200)
        snippet = content[start:end].replace('\n', ' ').strip()
        print(f"\n{kw} @ 0x{idx:x}:")
        print(f"  ...{snippet[:150]}...")

# Search for class definitions containing 'League'
print("\n\nLeague class definitions:")
import re
for m in re.finditer(r'class\s+(\w*League\w*)', content):
    name = m.group(1)
    start = m.start()
    # Get full class declaration
    end = content.find('{', start)
    if end > 0:
        header = content[start:end].strip()
        print(f"  {header}")
