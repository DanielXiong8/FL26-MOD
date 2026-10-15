# -*- coding: utf-8 -*-
"""
ClubPlayer: find correct record format by trying different offsets and sizes.
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

# We know team 20026 records exist at 0x2a054 with 17-byte spacing
# Let's check what's BEFORE that section
# First uint32 = 1862. If this is count of something...

# Let's try: 1862 entries of 8 bytes (team_id + player_id) = 14896 bytes
# Then the remaining data starts at 4 + 14896 = 14900 = 0x3a34
print(f"\nIf section 1 = 1862 * 8 bytes:")
sec1_end = 4 + 1862 * 8
print(f"  Section 1: 0x4 - 0x{sec1_end:x} ({sec1_end} bytes)")
print(f"  Section 2 starts at: 0x{sec1_end:x}")
print(f"  Section 2 size: {len(raw) - sec1_end} bytes")
print(f"  Section 2 records (17 bytes): {(len(raw) - sec1_end) / 17:.1f}")

# Parse section 1 as team_id + player_id pairs
print(f"\nSection 1 (8-byte records):")
for i in range(10):
    off = 4 + i * 8
    tid = struct.unpack_from("<I", raw, off)[0]
    pid = struct.unpack_from("<I", raw, off + 4)[0]
    print(f"  [{i}] team={tid} player={pid}")
print(f"  ...")
for i in range(1855, 1862):
    off = 4 + i * 8
    tid = struct.unpack_from("<I", raw, off)[0]
    pid = struct.unpack_from("<I", raw, off + 4)[0]
    print(f"  [{i}] team={tid} player={pid}")

# Parse section 2 as 17-byte records
print(f"\nSection 2 (17-byte records, starting at 0x{sec1_end:x}):")
rec_size = 17
sec2_data = raw[sec1_end:]
num_recs = len(sec2_data) // rec_size
print(f"  Records: {num_recs} (remaining: {len(sec2_data) % rec_size} bytes)")

# Check first 10 records
valid = 0
for i in range(min(10, num_recs)):
    off = i * rec_size
    tid = struct.unpack_from("<I", sec2_data, off)[0]
    pid = struct.unpack_from("<I", sec2_data, off + 4)[0]
    f1 = struct.unpack_from("<I", sec2_data, off + 8)[0]
    f2 = struct.unpack_from("<I", sec2_data, off + 12)[0]
    f3 = sec2_data[off + 16]
    ok = 10000 <= tid <= 40000 and 100 <= pid <= 200000
    if ok: valid += 1
    print(f"  [{i}] team={tid} player={pid} f1={f1} f2={f2} f3={f3} {'OK' if ok else '?'}")

# Count valid records
valid_total = 0
teams = set()
players = set()
for i in range(num_recs):
    off = i * rec_size
    tid = struct.unpack_from("<I", sec2_data, off)[0]
    pid = struct.unpack_from("<I", sec2_data, off + 4)[0]
    if 10000 <= tid <= 40000 and 100 <= pid <= 200000:
        valid_total += 1
        teams.add(tid)
        players.add(pid)

print(f"\n  Valid records: {valid_total}/{num_recs}")
print(f"  Unique teams: {len(teams)}")
print(f"  Unique players: {len(players)}")
if teams:
    print(f"  Team range: {min(teams)} - {max(teams)}")
if players:
    print(f"  Player range: {min(players)} - {max(players)}")

# Check team 20026
team_20026 = []
for i in range(num_recs):
    off = i * rec_size
    tid = struct.unpack_from("<I", sec2_data, off)[0]
    pid = struct.unpack_from("<I", sec2_data, off + 4)[0]
    if tid == 20026:
        f1 = struct.unpack_from("<I", sec2_data, off + 8)[0]
        f2 = struct.unpack_from("<I", sec2_data, off + 12)[0]
        f3 = sec2_data[off + 16]
        team_20026.append((pid, f1, f2, f3))

print(f"\n  Team 20026 players: {len(team_20026)}")
for pid, f1, f2, f3 in team_20026:
    print(f"    player={pid} f1={f1} f2={f2} f3={f3}")

# Check if pid 100242 is there
print(f"\n  pid 100242 in section 2: ", end="")
found = False
for i in range(num_recs):
    off = i * rec_size
    pid = struct.unpack_from("<I", sec2_data, off + 4)[0]
    if pid == 100242:
        tid = struct.unpack_from("<I", sec2_data, off)[0]
        print(f"YES (team={tid})")
        found = True
        break
if not found:
    print("NO")

# Check remaining bytes
remaining = len(sec2_data) % rec_size
if remaining > 0:
    print(f"\n  Trailing bytes after section 2: {remaining}")
    tail = sec2_data[num_recs * rec_size:]
    print(f"  Tail hex: {tail.hex()}")
