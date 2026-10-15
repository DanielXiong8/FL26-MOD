# -*- coding: utf-8 -*-
"""
Phase 4A: Build minimal new static player + inject into League.
Steps:
1. Add new player to Players (plyrcsv0)
2. Add new player to ClubPlayer (team assignment)
3. Rebuild gamedata.unity3d with modified TextAssets
4. Replace in APK, sign, install
"""
import struct, sys, io, os, shutil, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

# ── Config ──
TEST_PID = 180001
TEST_NAME = "CustomLeagueTest"
TEST_ATTRS = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]
TEST_TEAM = 20026  # Team with only 3 players in MasterLeaguePlayer (small, easy to spot)
TEST_YEAR = 2000

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_new_player.unity3d'

# ── Step 1: Parse and modify Players ──
print("=" * 60)
print("Step 1: Add new player to Players")
print("=" * 60)

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

env = UnityPy.load(BUNDLE_SRC)
players_raw = None
players_obj = None
clubplayer_raw = None
clubplayer_obj = None

for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name == 'Players':
            data = d.m_Script
            players_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
            players_obj = obj
        elif name == 'ClubPlayer':
            data = d.m_Script
            clubplayer_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
            clubplayer_obj = obj

if not players_raw:
    print("ERROR: Players not found!")
    sys.exit(1)

nations, recs = parse_plyrcsv0(players_raw)
print(f"Original: {len(recs)} players, {len(players_raw)} bytes")

# Add new player
new_rec = {
    "pid": TEST_PID,
    "name": TEST_NAME,
    "fa": 0, "fb": 0, "fc": 0,
    "nat": 0,  # England
    "b1": 0, "b16": 0, "b0": 0,
    "attrs": TEST_ATTRS,
    "tail16": 0, "tail8": 0,
    "year": TEST_YEAR
}
new_recs = recs + [new_rec]
new_players_raw = serialize_plyrcsv0(nations, new_recs)
print(f"Modified: {len(new_recs)} players, {len(new_players_raw)} bytes (delta=+{len(new_players_raw)-len(players_raw)})")

# ── Step 2: Parse and modify ClubPlayer ──
print("\n" + "=" * 60)
print("Step 2: Add new player to ClubPlayer")
print("=" * 60)

if clubplayer_raw:
    print(f"ClubPlayer: {len(clubplayer_raw)} bytes")
    count = struct.unpack_from("<I", clubplayer_raw, 0)[0]
    print(f"ClubPlayer count: {count}")

    # Parse existing records: each is team_id(4) + player_id(4) = 8 bytes
    # But wait - the hex dump showed:
    #   46 07 00 00 = 1862 (count)
    #   96 00 00 00 = 150 (first team_id?)
    #   13 00 00 00 = 19 (first player_id?)
    #   97 00 00 00 = 151 (second team_id?)
    #   13 00 00 00 = 19 (second player_id?)
    # So format is: count(4) + [team_id(4) + player_id(4)] * count

    records = []
    off = 4
    for i in range(count):
        tid = struct.unpack_from("<I", clubplayer_raw, off)[0]; off += 4
        pid = struct.unpack_from("<I", clubplayer_raw, off)[0]; off += 4
        records.append((tid, pid))

    print(f"Parsed {len(records)} ClubPlayer records")
    print(f"First 10: {records[:10]}")
    print(f"Last 10: {records[-10:]}")

    # Check if TEST_PID already exists
    existing = [r for r in records if r[1] == TEST_PID]
    if existing:
        print(f"WARNING: PID {TEST_PID} already exists in ClubPlayer!")
    else:
        print(f"PID {TEST_PID} not in ClubPlayer (good)")

    # Check team 20026 players
    team_players = [r for r in records if r[0] == TEST_TEAM]
    print(f"\nTeam {TEST_TEAM} players in ClubPlayer: {len(team_players)}")
    for tid, pid in team_players:
        print(f"  team={tid} player={pid}")

    # Add new record
    new_record = (TEST_TEAM, TEST_PID)
    new_records = records + [new_record]
    print(f"\nAdded: team={TEST_TEAM} player={TEST_PID}")
    print(f"New count: {len(new_records)}")

    # Serialize
    new_cp = struct.pack("<I", len(new_records))
    for tid, pid in new_records:
        new_cp += struct.pack("<I", tid)
        new_cp += struct.pack("<I", pid)
    print(f"New ClubPlayer size: {len(new_cp)} bytes (delta=+{len(new_cp)-len(clubplayer_raw)})")
else:
    print("ClubPlayer not found!")
    new_cp = None

# ── Step 3: Rebuild bundle ──
print("\n" + "=" * 60)
print("Step 3: Rebuild gamedata.unity3d")
print("=" * 60)

os.makedirs(os.path.dirname(BUNDLE_DST), exist_ok=True)

# Copy source
shutil.copy2(BUNDLE_SRC, BUNDLE_DST)

# Load and modify
env2 = UnityPy.load(BUNDLE_DST)
modified_count = 0

for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name == 'Players':
            # UnityPy TextAsset.m_Script expects str (uses surrogateescape internally)
            d.m_Script = new_players_raw.decode('utf-8', errors='surrogateescape')
            d.save()
            modified_count += 1
            print(f"  Replaced Players ({len(new_players_raw)} bytes)")
        elif name == 'ClubPlayer' and new_cp:
            d.m_Script = new_cp.decode('utf-8', errors='surrogateescape')
            d.save()
            modified_count += 1
            print(f"  Replaced ClubPlayer ({len(new_cp)} bytes)")

if modified_count > 0:
    with open(BUNDLE_DST, 'wb') as f:
        f.write(env2.file.save())
    print(f"\nSaved: {BUNDLE_DST}")
    print(f"Size: {os.path.getsize(BUNDLE_DST)} bytes (original: {os.path.getsize(BUNDLE_SRC)})")
else:
    print("ERROR: No TextAssets modified!")
    sys.exit(1)

print("\n" + "=" * 60)
print("Phase 4A Complete - Ready for APK injection")
print("=" * 60)
print(f"New player: pid={TEST_PID} name={TEST_NAME}")
print(f"Team: {TEST_TEAM}")
print(f"Attributes: {TEST_ATTRS}")
print(f"Nation: England (index 0)")
