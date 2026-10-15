# -*- coding: utf-8 -*-
"""
Phase 4A v9:
- pid = 175923 (next sequential ID, preserves Players/PA table sorted order)
- Players: append record, clone Ralla fields, year=1998, b1=14, attrs 81..97
- PlayerAppearanceTable: append entry for 175923, clone Ralla's 17B appearance data
- ClubPlayer: REPLACE London Red's least useful reserve player (or insert at physical end)
  To test safely: try BOTH:
  Approach A (pure add): sec1 20030 cnt 24->25, insert at 9386, f1=99
"""
import struct, sys, io, os, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

TEST_PID = 175923  # immediately follows max existing pid 175922
TEST_NAME = "CustomLeagueTest"
TEST_ATTRS = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]
TEST_TEAM = 20030
TEST_YEAR = 1998
TEMPLATE_PID = 103346  # Ralla

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_v9.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\fl26_mod_4a_v9.apk'

BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
KEYSTORE = r'C:\FL26_Mod\build\fl26_test.keystore'

env = UnityPy.load(BUNDLE_SRC)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            raw = d.m_Script
            assets[name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

# Players
def parse_plyrcsv0(raw):
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

nations, recs = parse_plyrcsv0(assets['Players'])
tmpl = next(r for r in recs if r["pid"] == TEMPLATE_PID)
new_player = {
    "pid": TEST_PID, "name": TEST_NAME,
    "fa": tmpl["fa"], "fb": tmpl["fb"], "fc": tmpl["fc"], "nat": tmpl["nat"],
    "b1": 14, "b16": tmpl["b16"], "b0": tmpl["b0"],
    "attrs": TEST_ATTRS,
    "tail16": tmpl["tail16"], "tail8": tmpl["tail8"], "year": TEST_YEAR
}
new_players_raw = serialize_plyrcsv0(nations, recs + [new_player])
print(f"[Players] 175923 appended, {len(recs)} -> {len(recs)+1}")

# ClubPlayer: insert at 9386 (end of 20030 block), sec1 20030 count 24->25
raw = assets['ClubPlayer']
n1 = struct.unpack_from("<I", raw, 0)[0]
sec1 = [list(struct.unpack_from("<II", raw, 4 + i*8)) for i in range(n1)]
sec2 = []
off = 4 + n1*8
while off + 17 <= len(raw):
    tid, pid, f1, f2 = struct.unpack_from("<IIII", raw, off)
    sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": raw[off+16]})
    off += 17
team_rows = [i for i, r in enumerate(sec2) if r["team_id"] == TEST_TEAM]
insert_pos = team_rows[-1] + 1
for e in sec1:
    if e[0] == TEST_TEAM:
        e[1] += 1
new_rec = {"team_id": TEST_TEAM, "player_id": TEST_PID, "f1": 99, "f2": 6912, "f3": 0}
new_sec2 = sec2[:insert_pos] + [new_rec] + sec2[insert_pos:]
out = io.BytesIO()
out.write(struct.pack("<I", len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack("<II", tid, cnt))
for r in new_sec2:
    out.write(struct.pack("<IIII", r["team_id"], r["player_id"], r["f1"], r["f2"]))
    out.write(bytes([r["f3"]]))
new_clubplayer_raw = out.getvalue()
print(f"[ClubPlayer] sec2 {len(sec2)} -> {len(new_sec2)}, insert@{insert_pos}")

# PlayerAppearanceTable: append 175923
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
idx_entries = [struct.unpack_from("<II", pa, 4 + i*8) for i in range(n)]
data_start = 4 + n*8
data = pa[data_start:]
t_off = dict(idx_entries)[TEMPLATE_PID]
t_rec = pa[t_off:t_off+21]
new_app_rec = struct.pack("<I", TEST_PID) + t_rec[4:]
new_n = n + 1
new_data_start = 4 + new_n*8
new_rec_off = new_data_start + len(data)
out = io.BytesIO()
out.write(struct.pack("<I", new_n))
for k, o in idx_entries:
    out.write(struct.pack("<II", k, o + 8))
out.write(struct.pack("<II", TEST_PID, new_rec_off))
out.write(data)
out.write(new_app_rec)
new_pa = out.getvalue()
print(f"[Appearance] entries {n} -> {new_n}")

# Rebuild bundle
os.makedirs(os.path.dirname(BUNDLE_DST), exist_ok=True)
shutil.copy2(BUNDLE_SRC, BUNDLE_DST)
env2 = UnityPy.load(BUNDLE_DST)
modified = 0
payloads = {'Players': new_players_raw, 'ClubPlayer': new_clubplayer_raw, 'PlayerAppearanceTable': new_pa}
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name in payloads:
            d.m_Script = payloads[name].decode('utf-8', errors='surrogateescape')
            d.save(); modified += 1
with open(BUNDLE_DST, 'wb') as f:
    f.write(env2.file.save())

# APK
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

env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([ZIPALIGN, '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
os.replace(aligned, DST_APK)
r = subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE, '--ks-pass', 'pass:fl26modtest',
                    '--ks-key-alias', 'fl26test', DST_APK], capture_output=True, text=True, env=env_vars)
print("sign:", 'OK' if r.returncode == 0 else r.stderr[-500:])

print("\nInstalling...")
r = subprocess.run([ADB, 'install', '-r', DST_APK], capture_output=True, text=True, timeout=180)
print(r.stdout.strip() or r.stderr.strip())
print(f"\nDONE v9: pid={TEST_PID}")
