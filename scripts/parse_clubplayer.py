# -*- coding: utf-8 -*-
"""
ClubPlayer: correct 17-byte record parser + injector.
Format: count(4) + [team_id(4) + player_id(4) + f1(4) + f2(4) + f3(1)] × N
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

RECORD_SIZE = 17

def parse_clubplayer(raw: bytes):
    count = struct.unpack_from("<I", raw, 0)[0]
    records = []
    off = 4
    for i in range(count):
        if off + RECORD_SIZE > len(raw):
            print(f"WARNING: truncated at record {i}")
            break
        team_id = struct.unpack_from("<I", raw, off)[0]
        player_id = struct.unpack_from("<I", raw, off + 4)[0]
        f1 = struct.unpack_from("<I", raw, off + 8)[0]
        f2 = struct.unpack_from("<I", raw, off + 12)[0]
        f3 = raw[off + 16]
        records.append({
            "team_id": team_id,
            "player_id": player_id,
            "f1": f1,
            "f2": f2,
            "f3": f3,
            "_offset": off
        })
        off += RECORD_SIZE
    consumed = off
    return count, records, consumed, len(raw)

def serialize_clubplayer(records) -> bytes:
    out = struct.pack("<I", len(records))
    for r in records:
        out += struct.pack("<I", r["team_id"])
        out += struct.pack("<I", r["player_id"])
        out += struct.pack("<I", r["f1"])
        out += struct.pack("<I", r["f2"])
        out += bytes([r["f3"]])
    return out

# Load and parse
env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

count, records, consumed, total = parse_clubplayer(raw)
print(f"ClubPlayer: {count} records declared, {len(records)} parsed")
print(f"Consumed: {consumed}/{total} bytes ({consumed/total*100:.1f}%)")
print(f"Remaining: {total - consumed} bytes")

# Check remaining bytes
if consumed < total:
    remaining = raw[consumed:consumed+64]
    print(f"Remaining hex (first 64): {remaining.hex()}")
    # Check if remaining is all zeros or has structure
    non_zero = sum(1 for b in raw[consumed:] if b != 0)
    print(f"Non-zero bytes in remaining: {non_zero}")

# Analyze team 20026
team_20026 = [r for r in records if r["team_id"] == 20026]
print(f"\nTeam 20026 records: {len(team_20026)}")
for r in team_20026:
    print(f"  player={r['player_id']} f1={r['f1']} f2={r['f2']} f3={r['f3']}")

# Analyze team 20051 (from MasterLeaguePlayer)
team_20051 = [r for r in records if r["team_id"] == 20051]
print(f"\nTeam 20051 records: {len(team_20051)}")
for r in team_20051:
    print(f"  player={r['player_id']} f1={r['f1']} f2={r['f2']} f3={r['f3']}")

# Check if pid 100242 is in ClubPlayer
pids_in_cp = set(r["player_id"] for r in records)
print(f"\npid 100242 in ClubPlayer: {100242 in pids_in_cp}")
print(f"pid 100373 in ClubPlayer: {100373 in pids_in_cp}")
print(f"pid 111024 in ClubPlayer: {111024 in pids_in_cp}")

# Stats
all_teams = set(r["team_id"] for r in records)
all_pids = set(r["player_id"] for r in records)
print(f"\nTotal teams: {len(all_teams)}")
print(f"Total unique players: {len(all_pids)}")
print(f"Team ID range: {min(all_teams)} - {max(all_teams)}")
print(f"Player ID range: {min(all_pids)} - {max(all_pids)}")

# Add new player to team 20026
NEW_REC = {
    "team_id": 20026,
    "player_id": 180001,
    "f1": 25,  # copy from a similar player
    "f2": 0,
    "f3": 0
}

new_records = records + [NEW_REC]
new_raw = serialize_clubplayer(new_records)
print(f"\nNew ClubPlayer: {len(new_records)} records, {len(new_raw)} bytes")
print(f"Delta: +{len(new_raw) - len(raw)} bytes")

# Verify roundtrip
count2, records2, consumed2, total2 = parse_clubplayer(new_raw)
print(f"Roundtrip: {count2} records, consumed {consumed2}/{total2}")
new_pids = set(r["player_id"] for r in records2)
print(f"New pid 180001 in roundtrip: {180001 in new_pids}")
