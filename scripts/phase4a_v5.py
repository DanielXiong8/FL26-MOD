# -*- coding: utf-8 -*-
"""
Phase 4A v5: Fix Age, Position, and Appearance issues.
"""
import struct, sys, io, os, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

TEST_PID = 180001
TEST_NAME = "CustomLeagueTest"
TEST_ATTRS = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]
TEST_TEAM = 20030  # Arsenal

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_v5.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\fl26_mod_4a_v5.apk'

BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
KEYSTORE = r'C:\FL26_Mod\build\fl26_test.keystore'

def parse_plyrcsv0(raw):
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

def serialize_plyrcsv0(nations, recs):
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

def parse_clubplayer(raw):
    count = struct.unpack_from("<I", raw, 0)[0]
    sec1 = []
    off = 4
    for i in range(count):
        tid = struct.unpack_from("<I", raw, off)[0]
        cnt = struct.unpack_from("<I", raw, off + 4)[0]
        sec1.append((tid, cnt))
        off += 8
    sec2 = []
    while off + 17 <= len(raw):
        tid = struct.unpack_from("<I", raw, off)[0]
        pid = struct.unpack_from("<I", raw, off + 4)[0]
        f1 = struct.unpack_from("<I", raw, off + 8)[0]
        f2 = struct.unpack_from("<I", raw, off + 12)[0]
        f3 = raw[off + 16]
        sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": f3})
        off += 17
    return sec1, sec2

def serialize_clubplayer(sec1, sec2):
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

# Load
env = UnityPy.load(BUNDLE_SRC)
players_raw = clubplayer_raw = None
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

# Analyze existing players to find correct year/position values
nations, recs = parse_plyrcsv0(players_raw)

# Find Arsenal players to see their year values
print("Existing Arsenal players year values:")
for r in recs:
    if r["pid"] in [103346, 110947, 103281, 103643, 119091]:
        print(f"  {r['name']}: year={r['year']} b1={r['b1']} b16={r['b16']} b0={r['b0']}")

# Check year distribution
years = [r["year"] for r in recs]
print(f"\nYear distribution: min={min(years)} max={max(years)}")
print(f"Year 2000 count: {sum(1 for y in years if y == 2000)}")
print(f"Year 1990-2000 count: {sum(1 for y in years if 1990 <= y <= 2000)}")

# Find a good year value (e.g., 1998 for ~28 years old)
GOOD_YEAR = 1998
print(f"Using year={GOOD_YEAR} (age ~{2026-GOOD_YEAR})")

# Position analysis: check b1 values for known positions
print("\nPosition analysis (b1 field):")
# Known positions from Arsenal:
# Ralla (GK), Hincapie (MF), Gabrier (MF), Sariba (MF), Moskera (MF)
# Let's find their b1 values
for r in recs:
    if r["name"] in ["Ralla", "Hincapie", "Gabrier", "Sariba", "Moskera", "Odegard", "Sakar", "Haverts"]:
        print(f"  {r['name']}: b1={r['b1']}")

# b1 values seen: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
# Let's use b1=14 (FW) for striker, or b1=2 (DF) for defender
# User wants ST (striker), so let's try b1=14

# Check b16 and b0
print("\nb16/b0 values for known players:")
for r in recs:
    if r["name"] in ["Ralla", "Hincapie", "Gabrier"]:
        print(f"  {r['name']}: b16={r['b16']} b0={r['b0']}")

# Create new player with corrected values
new_player = {
    "pid": TEST_PID, "name": TEST_NAME,
    "fa": 0, "fb": 0, "fc": 0, "nat": 0,  # England
    "b1": 14, "b16": 0, "b0": 0,  # b1=14 for FW/ST
    "attrs": TEST_ATTRS,
    "tail16": 0, "tail8": 0,
    "year": GOOD_YEAR  # 1998 for age ~28
}
new_recs = recs + [new_player]
new_players_raw = serialize_plyrcsv0(nations, new_recs)
print(f"\nNew player: year={GOOD_YEAR}, b1=14 (FW)")

# Modify ClubPlayer
sec1, sec2 = parse_clubplayer(clubplayer_raw)
new_sec1 = []
for tid, cnt in sec1:
    if tid == TEST_TEAM:
        new_sec1.append((tid, cnt + 1))
    else:
        new_sec1.append((tid, cnt))

new_cp_rec = {
    "team_id": TEST_TEAM, "player_id": TEST_PID,
    "f1": 1,  # High priority
    "f2": 6912,
    "f3": 0
}
new_sec2 = sec2 + [new_cp_rec]
new_clubplayer_raw = serialize_clubplayer(new_sec1, new_sec2)

# Rebuild bundle
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
        elif name == 'ClubPlayer':
            d.m_Script = new_clubplayer_raw.decode('utf-8', errors='surrogateescape')
            d.save()
            modified += 1
with open(BUNDLE_DST, 'wb') as f:
    f.write(env2.file.save())
print(f"Bundle: {os.path.getsize(BUNDLE_DST):,} bytes")

# Inject into APK
os.makedirs(os.path.dirname(DST_APK), exist_ok=True)
with zipfile.ZipFile(SRC_APK, 'r') as zin:
    with zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/gamedata.unity3d':
                with open(BUNDLE_DST, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(DST_APK + '.tmp', DST_APK)

# Zipalign + Sign
env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([ZIPALIGN, '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
os.replace(aligned, DST_APK)
subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE, '--ks-pass', 'pass:fl26modtest',
                '--ks-key-alias', 'fl26test', DST_APK], capture_output=True, env=env_vars)

# Install
r = subprocess.run([ADB, 'install', '-r', DST_APK], capture_output=True, text=True, timeout=120)
print(r.stdout.strip())

print(f"\n{'='*60}")
print(f"DONE - v5 with corrected year={GOOD_YEAR}, position=FW")
print(f"{'='*60}")
