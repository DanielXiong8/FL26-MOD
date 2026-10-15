# -*- coding: utf-8 -*-
"""
Phase 4A.2: Determine safe PlayerID for new static player.
Phase 4A.3: Create minimal new Player record.
Phase 4A.4: Analyze League roster source (MasterLeaguePlayer vs ClubPlayer).
"""
import struct, sys, io, os, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def parse_plyrcsv0(raw: bytes):
    assert raw[:8] == b"plyrcsv0"
    off = 8
    ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
    nations = []
    for _ in range(ncnt):
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
    recs = []
    for i in range(pcnt):
        pid = struct.unpack_from("<I", raw, off)[0]; off += 4
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16 = struct.unpack_from("<H", raw, off)[0]; off += 2
        tail8 = raw[off]; off += 1
        year = struct.unpack_from("<I", raw, off)[0]; off += 4
        recs.append({"pid": pid, "name": name, "fa": fa, "fb": fb, "fc": fc, "nat": nat,
                     "b1": b1, "b16": b16, "b0": b0, "attrs": attrs,
                     "tail16": tail16, "tail8": tail8, "year": year})
    return nations, recs

def serialize_plyrcsv0(nations, recs) -> bytes:
    out = io.BytesIO()
    out.write(b"plyrcsv0")
    out.write(struct.pack("<H", len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le')
        out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
    out.write(struct.pack("<I", len(recs)))
    for r in recs:
        out.write(struct.pack("<I", r["pid"]))
        nb = r["name"].encode('utf-16-le', errors='replace')
        out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
        out.write(struct.pack("<HHHH", r["fa"], r["fb"], r["fc"], r["nat"]))
        out.write(bytes([r["b1"], r["b16"], r["b0"]]))
        out.write(bytes(r["attrs"]))
        out.write(struct.pack("<H", r["tail16"]))
        out.write(bytes([r["tail8"]]))
        out.write(struct.pack("<I", r["year"]))
    return out.getvalue()

# ── Phase 4A.2: Find max PlayerID ──
print("=" * 50)
print("Phase 4A.2: PlayerID Range Analysis")
print("=" * 50)

import UnityPy
env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
raw = None
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

nations, recs = parse_plyrcsv0(raw)

# Analyze ID distribution
pids = sorted([r["pid"] for r in recs])
max_pid = pids[-1]
min_pid = pids[0]
print(f"Total players: {len(recs)}")
print(f"ID range: {min_pid} - {max_pid}")

# Find gaps in ID space
gaps = []
for i in range(1, len(pids)):
    gap = pids[i] - pids[i-1]
    if gap > 100:
        gaps.append((pids[i-1], pids[i], gap))
if gaps:
    print(f"\nLarge gaps (>100) in ID space:")
    for prev, nxt, gap in gaps[:10]:
        print(f"  {prev} -> {nxt} (gap={gap})")
else:
    print("\nNo large gaps found")

# Find ID clusters
print(f"\nID distribution histogram:")
ranges = [(200, 50000), (50000, 100000), (100000, 150000), (150000, 176000)]
for lo, hi in ranges:
    count = sum(1 for p in pids if lo <= p < hi)
    print(f"  {lo}-{hi}: {count} players")

# Safe test ID: pick well above max
TEST_PID = 180001
print(f"\nChosen TEST_PID: {TEST_PID}")
print(f"  (max existing: {max_pid}, margin: {TEST_PID - max_pid})")

# ── Phase 4A.3: Create minimal new player ──
print("\n" + "=" * 50)
print("Phase 4A.3: Create Minimal New Player")
print("=" * 50)

NEW_PLAYER = {
    "pid": TEST_PID,
    "name": "CustomLeagueTest",
    "fa": 0, "fb": 0, "fc": 0,
    "nat": 0,  # use first nation (will check what index 0 is)
    "b1": 0, "b16": 0, "b0": 0,
    "attrs": [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97],
    "tail16": 0, "tail8": 0,
    "year": 2000
}

# Find nation index for a reasonable default
print(f"Available nations (first 10): {nations[:10]}")
# Use England if available
try:
    eng_idx = nations.index("England")
    NEW_PLAYER["nat"] = eng_idx
    print(f"Using nation: England (index {eng_idx})")
except ValueError:
    print(f"Using nation: {nations[0]} (index 0)")

# Create modified records list
new_recs = recs + [NEW_PLAYER]
new_raw = serialize_plyrcsv0(nations, new_recs)
print(f"\nOriginal size: {len(raw)} bytes")
print(f"New size: {len(new_raw)} bytes (delta=+{len(new_raw)-len(raw)})")
print(f"New player count: {len(new_recs)}")

# Verify new player parseable
nations2, recs2 = parse_plyrcsv0(new_raw)
found = [r for r in recs2 if r["pid"] == TEST_PID]
if found:
    r = found[0]
    print(f"New player verified: pid={r['pid']} name={r['name']} attrs={r['attrs'][:5]}...")
else:
    print("ERROR: New player not found in re-parsed data!")

# Roundtrip check
assert len(new_raw) > len(raw), "New data should be larger"
print(f"Roundtrip serialize/parse: OK")

# Save new Players table bytes
out_path = r'C:\FL26_Mod\modified\players_new.bin'
with open(out_path, 'wb') as f:
    f.write(new_raw)
print(f"Saved: {out_path} ({len(new_raw)} bytes)")

# ── Phase 4A.4: League Roster Analysis ──
print("\n" + "=" * 50)
print("Phase 4A.4: League Roster Source Analysis")
print("=" * 50)

# MasterLeaguePlayer CSV
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'MasterLeaguePlayer':
        data = obj.read().m_Script
        text = data if isinstance(data, str) else data.decode('utf-8', errors='replace')
        lines = text.strip().split('\n')
        print(f"MasterLeaguePlayer: {len(lines)} lines")
        print(f"Header: {lines[0]}")
        # Count teams with players
        active_teams = 0
        total_player_refs = 0
        for line in lines[1:]:
            parts = line.strip().split(',')
            if len(parts) >= 2 and parts[1]:
                pids = parts[1].split('|')
                total_player_refs += len(pids)
                active_teams += 1
        print(f"Active teams: {active_teams}")
        print(f"Total player references: {total_player_refs}")
        # Show first 5 teams
        print("First 5 teams:")
        for line in lines[1:6]:
            print(f"  {line}")
        break

# ClubPlayer analysis
print("\nClubPlayer table:")
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        cp_bytes = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        print(f"ClubPlayer: {len(cp_bytes)} bytes")
        print(f"Magic: {cp_bytes[:8].decode('ascii', errors='replace')}")
        break

# Check if any existing team roster includes our test PID
print(f"\nTest PID {TEST_PID} in MasterLeaguePlayer? ", end="")
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'MasterLeaguePlayer':
        data = obj.read().m_Script
        text = data if isinstance(data, str) else data.decode('utf-8', errors='replace')
        if str(TEST_PID) in text:
            print("YES (WARNING!)")
        else:
            print("NO (good, ID is unused)")
        break

# Find a good target team (has few players, well-known)
print("\nCandidate target teams (small roster):")
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'MasterLeaguePlayer':
        data = obj.read().m_Script
        text = data if isinstance(data, str) else data.decode('utf-8', errors='replace')
        lines = text.strip().split('\n')
        for line in lines[1:]:
            parts = line.strip().split(',')
            if len(parts) >= 2 and parts[1]:
                pids = parts[1].split('|')
                if len(pids) <= 5:
                    print(f"  Team {parts[0]}: {len(pids)} players -> {parts[1][:60]}")
        break
