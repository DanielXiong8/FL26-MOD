# -*- coding: utf-8 -*-
"""
Phase 4A Final: Build new static player into gamedata.unity3d.
Correctly parses ClubPlayer (2 sections) and Players (plyrcsv0).
"""
import struct, sys, io, os, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

# ── Config ──
TEST_PID = 180001
TEST_NAME = "CustomLeagueTest"
TEST_ATTRS = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]
TEST_TEAM = 20026  # small team, 27 players
TEST_YEAR = 2000

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_new_player.unity3d'

# ── Players Parser ──
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

# ── ClubPlayer Parser ──
def parse_clubplayer(raw: bytes):
    count = struct.unpack_from("<I", raw, 0)[0]
    # Section 1: count * 8 bytes (team_id + player_count)
    sec1 = []
    off = 4
    for i in range(count):
        tid = struct.unpack_from("<I", raw, off)[0]
        cnt = struct.unpack_from("<I", raw, off + 4)[0]
        sec1.append((tid, cnt))
        off += 8
    # Section 2: 17-byte records
    sec2 = []
    while off + 17 <= len(raw):
        tid = struct.unpack_from("<I", raw, off)[0]
        pid = struct.unpack_from("<I", raw, off + 4)[0]
        f1 = struct.unpack_from("<I", raw, off + 8)[0]
        f2 = struct.unpack_from("<I", raw, off + 12)[0]
        f3 = raw[off + 16]
        sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": f3})
        off += 17
    return sec1, sec2, off

def serialize_clubplayer(sec1, sec2) -> bytes:
    out = struct.pack("<I", len(sec1))
    for tid, cnt in sec1:
        out += struct.pack("<I", tid)
        out += struct.pack("<I", cnt)
    for r in sec2:
        out += struct.pack("<I", r["team_id"])
        out += struct.pack("<I", r["player_id"])
        out += struct.pack("<I", r["f1"])
        out += struct.pack("<I", r["f2"])
        out += bytes([r["f3"]])
    return out

# ── Main ──
print("=" * 60)
print("Phase 4A: Build New Static Player")
print("=" * 60)

env = UnityPy.load(BUNDLE_SRC)
players_raw = None
clubplayer_raw = None

for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name == 'Players':
            data = d.m_Script
            players_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        elif name == 'ClubPlayer':
            data = d.m_Script
            clubplayer_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data

# ── Modify Players ──
print("\n--- Players ---")
nations, recs = parse_plyrcsv0(players_raw)
print(f"Original: {len(recs)} players")

new_player = {
    "pid": TEST_PID, "name": TEST_NAME,
    "fa": 0, "fb": 0, "fc": 0, "nat": 0,
    "b1": 0, "b16": 0, "b0": 0,
    "attrs": TEST_ATTRS,
    "tail16": 0, "tail8": 0, "year": TEST_YEAR
}
new_recs = recs + [new_player]
new_players_raw = serialize_plyrcsv0(nations, new_recs)
print(f"Modified: {len(new_recs)} players (+{len(new_players_raw)-len(players_raw)} bytes)")

# ── Modify ClubPlayer ──
print("\n--- ClubPlayer ---")
sec1, sec2, consumed = parse_clubplayer(clubplayer_raw)
print(f"Section 1: {len(sec1)} team entries")
print(f"Section 2: {len(sec2)} player records (consumed {consumed}/{len(clubplayer_raw)})")

# Update section 1: increment player count for team 20026
new_sec1 = []
for tid, cnt in sec1:
    if tid == TEST_TEAM:
        new_sec1.append((tid, cnt + 1))
        print(f"Team {tid}: count {cnt} -> {cnt+1}")
    else:
        new_sec1.append((tid, cnt))

# Add new record to section 2
# Copy f1/f2/f3 from an existing team 20026 player (use first one as template)
template = None
for r in sec2:
    if r["team_id"] == TEST_TEAM:
        template = r
        break

new_cp_rec = {
    "team_id": TEST_TEAM,
    "player_id": TEST_PID,
    "f1": template["f1"] if template else 25,
    "f2": template["f2"] if template else 0,
    "f3": template["f3"] if template else 0
}
new_sec2 = sec2 + [new_cp_rec]
new_clubplayer_raw = serialize_clubplayer(new_sec1, new_sec2)
print(f"Added player {TEST_PID} to team {TEST_TEAM}")
print(f"New ClubPlayer: {len(new_clubplayer_raw)} bytes (delta=+{len(new_clubplayer_raw)-len(clubplayer_raw)})")

# ── Rebuild bundle ──
print("\n--- Rebuild Bundle ---")
os.makedirs(os.path.dirname(BUNDLE_DST), exist_ok=True)
shutil.copy2(BUNDLE_SRC, BUNDLE_DST)

env2 = UnityPy.load(BUNDLE_DST)
modified = 0
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name == 'Players':
            d.m_Script = new_players_raw.decode('utf-8', errors='surrogateescape')
            d.save()
            modified += 1
            print(f"  Replaced Players ({len(new_players_raw)} bytes)")
        elif name == 'ClubPlayer':
            d.m_Script = new_clubplayer_raw.decode('utf-8', errors='surrogateescape')
            d.save()
            modified += 1
            print(f"  Replaced ClubPlayer ({len(new_clubplayer_raw)} bytes)")

if modified > 0:
    with open(BUNDLE_DST, 'wb') as f:
        f.write(env2.file.save())
    print(f"\nSaved: {BUNDLE_DST}")
    print(f"Size: {os.path.getsize(BUNDLE_DST):,} bytes (original: {os.path.getsize(BUNDLE_SRC):,})")
else:
    print("ERROR: No TextAssets modified!")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"New Player: pid={TEST_PID} name={TEST_NAME}")
print(f"Team: {TEST_TEAM}")
print(f"Attributes: {TEST_ATTRS}")
print(f"Nation: England (index 0)")
print(f"Players table: {len(new_recs)} records")
print(f"ClubPlayer: {len(new_sec2)} section-2 records")
print(f"Ready for APK injection")
