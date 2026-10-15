# -*- coding: utf-8 -*-
"""
ClubPlayer: find exact record boundaries by searching for known values as raw bytes.
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

# Search for known player IDs as LE uint32
known = {
    100526: "team 20026 player (from ClubPlayer index 43029)",
    111024: "team 20026 player (from ClubPlayer index 43046)",
    100242: "team 20026 player (from MasterLeaguePlayer)",
    103727: "team 20026 player (from MasterLeaguePlayer)",
    100373: "Reno (Fulham)",
}

for pid, desc in known.items():
    le = struct.pack("<I", pid)
    idx = raw.find(le)
    if idx >= 0:
        print(f"\npid {pid} ({desc}):")
        print(f"  LE found at byte offset 0x{idx:x}")
        # Show 68 bytes around it (one record)
        start = max(0, idx - 20)
        end = min(len(raw), idx + 48)
        for i in range(start, end, 16):
            hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, end-i)))
            marker = " <<<" if i <= idx < i + 16 else ""
            print(f"    {i:6x}: {hex_str}{marker}")
    else:
        print(f"\npid {pid} ({desc}): NOT FOUND as LE uint32")
        # Try BE
        be = struct.pack(">I", pid)
        idx = raw.find(be)
        if idx >= 0:
            print(f"  BE found at byte offset 0x{idx:x}")

# Also search for team 20026 as LE uint16 (0x3A4E)
team_le16 = struct.pack("<H", 20026)
indices = []
idx = 0
while True:
    idx = raw.find(team_le16, idx)
    if idx < 0:
        break
    indices.append(idx)
    idx += 1
print(f"\nTeam 20026 as LE uint16 (0x3A4E): {len(indices)} occurrences")
if indices:
    print(f"  First 10 offsets: {[hex(i) for i in indices[:10]]}")

# Search for team 20026 as LE uint32
team_le32 = struct.pack("<I", 20026)
indices32 = []
idx = 0
while True:
    idx = raw.find(team_le32, idx)
    if idx < 0:
        break
    indices32.append(idx)
    idx += 1
print(f"Team 20026 as LE uint32: {len(indices32)} occurrences")
if indices32:
    print(f"  Offsets: {[hex(i) for i in indices32[:20]]}")
    # Check spacing
    if len(indices32) > 1:
        spacings = [indices32[i+1] - indices32[i] for i in range(len(indices32)-1)]
        print(f"  Spacings: {spacings[:10]}")
