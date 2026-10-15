# -*- coding: utf-8 -*-
"""
Phase 4A v4: Differential test — move EXISTING player to Arsenal.
Pick a low-profile player from a different league, move to Arsenal.
If this works, ClubPlayer modification is effective.
If this fails too, the issue is deeper (League uses different roster source).
"""
import struct, sys, io, os, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

# Pick a player from a small/obscure team
# From ClubPlayer analysis: team 10908 has 22 players (small team)
# Let's pick the first player from team 10908 and move to Arsenal (20030)
SOURCE_TEAM = 10908
TARGET_TEAM = 20030  # Arsenal

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_differential.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\fl26_mod_4a_differential.apk'

BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
KEYSTORE = r'C:\FL26_Mod\build\fl26_test.keystore'

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
clubplayer_raw = None
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        clubplayer_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

sec1, sec2 = parse_clubplayer(clubplayer_raw)

# Find a player from source team
source_players = [r for r in sec2 if r["team_id"] == SOURCE_TEAM]
if not source_players:
    print(f"No players found in team {SOURCE_TEAM}")
    sys.exit(1)

# Pick first player from source team
moved_player = source_players[0]
moved_pid = moved_player["player_id"]
print(f"Moving player {moved_pid} from team {SOURCE_TEAM} to team {TARGET_TEAM}")

# Update section 1: decrement source, increment target
new_sec1 = []
for tid, cnt in sec1:
    if tid == SOURCE_TEAM:
        new_sec1.append((tid, cnt - 1))
        print(f"Team {tid}: {cnt} -> {cnt-1}")
    elif tid == TARGET_TEAM:
        new_sec1.append((tid, cnt + 1))
        print(f"Team {tid}: {cnt} -> {cnt+1}")
    else:
        new_sec1.append((tid, cnt))

# Update section 2: change team_id of moved player
new_sec2 = []
for r in sec2:
    if r["player_id"] == moved_pid and r["team_id"] == SOURCE_TEAM:
        new_r = dict(r)
        new_r["team_id"] = TARGET_TEAM
        new_r["f1"] = 1  # High priority
        new_sec2.append(new_r)
        print(f"  Moved: team {r['team_id']} -> {TARGET_TEAM}, f1 {r['f1']} -> 1")
    else:
        new_sec2.append(r)

new_clubplayer_raw = serialize_clubplayer(new_sec1, new_sec2)
print(f"ClubPlayer: {len(sec2)} -> {len(new_sec2)} records (same size)")

# Rebuild bundle
os.makedirs(os.path.dirname(BUNDLE_DST), exist_ok=True)
shutil.copy2(BUNDLE_SRC, BUNDLE_DST)
env2 = UnityPy.load(BUNDLE_DST)
for obj in env2.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        d = obj.read(check_read=False)
        d.m_Script = new_clubplayer_raw.decode('utf-8', errors='surrogateescape')
        d.save()
        break
with open(BUNDLE_DST, 'wb') as f:
    f.write(env2.file.save())
print(f"Bundle saved: {os.path.getsize(BUNDLE_DST):,} bytes")

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

print(f"\nDifferential test: moved player {moved_pid} from team {SOURCE_TEAM} to {TARGET_TEAM}")
print(f"If this player appears in Arsenal squad, ClubPlayer modification works.")
