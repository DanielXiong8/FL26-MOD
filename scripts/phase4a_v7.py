# -*- coding: utf-8 -*-
"""
Phase 4A v7: FIX v6 bugs.
- ClubPlayer: insert at PHYSICAL end of team 20030 block (idx 9386), not sec1-order position.
- f1=99 (avoid duplicate with Ralla f1=1), f2=6912.
- Players record: clone fa/fb/fc/nat/b0/tail16 from template (Ralla pid 103346) so foot displays.
- year=1998, b1=14 (FW), attrs 81..97 unchanged.
"""
import struct, sys, io, os, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

TEST_PID = 180001
TEST_NAME = "CustomLeagueTest"
TEST_ATTRS = [81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97]
TEST_TEAM = 20030
TEST_YEAR = 1998
TEMPLATE_PID = 103346  # Ralla

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_v7.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\fl26_mod_4a_v7.apk'

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

print("=" * 60)
print("Phase 4A v7: correct physical insertion + template fields")
print("=" * 60)

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

# --- Players: clone template fields ---
nations, recs = parse_plyrcsv0(players_raw)
tmpl = next(r for r in recs if r["pid"] == TEMPLATE_PID)
print(f"Template {TEMPLATE_PID} ({tmpl['name']}): fa={tmpl['fa']} fb={tmpl['fb']} fc={tmpl['fc']} nat={tmpl['nat']} b0={tmpl['b0']} tail16={tmpl['tail16']}")

new_player = {
    "pid": TEST_PID, "name": TEST_NAME,
    "fa": tmpl["fa"], "fb": tmpl["fb"], "fc": tmpl["fc"], "nat": tmpl["nat"],
    "b1": 14, "b16": tmpl["b16"], "b0": tmpl["b0"],
    "attrs": TEST_ATTRS,
    "tail16": tmpl["tail16"], "tail8": tmpl["tail8"], "year": TEST_YEAR
}
new_recs = recs + [new_player]
new_players_raw = serialize_plyrcsv0(nations, new_recs)
print(f"Players: {len(recs)} -> {len(new_recs)}, bytes {len(players_raw)} -> {len(new_players_raw)}")

# sanity: original bytes must be a prefix-equal re-encode; verify by re-serializing originals
check = serialize_plyrcsv0(nations, recs)
print(f"roundtrip byte-exact: {check == players_raw}")

# --- ClubPlayer: insert at physical end of team block ---
sec1, sec2 = parse_clubplayer(clubplayer_raw)
team_records = [i for i, r in enumerate(sec2) if r["team_id"] == TEST_TEAM]
insert_pos = team_records[-1] + 1
print(f"team {TEST_TEAM} block: {team_records[0]}..{team_records[-1]}, insert at {insert_pos}")
print(f"record at insert_pos (should be next team): {sec2[insert_pos]}")

new_sec1 = [(tid, cnt + 1) if tid == TEST_TEAM else (tid, cnt) for tid, cnt in sec1]
new_cp_rec = {"team_id": TEST_TEAM, "player_id": TEST_PID, "f1": 99, "f2": 6912, "f3": 0}
new_sec2 = sec2[:insert_pos] + [new_cp_rec] + sec2[insert_pos:]
new_clubplayer_raw = serialize_clubplayer(new_sec1, new_sec2)
print(f"ClubPlayer: sec2 {len(sec2)} -> {len(new_sec2)}, bytes {len(clubplayer_raw)} -> {len(new_clubplayer_raw)}")

# verify contiguity: every team's records contiguous in new_sec2
from collections import defaultdict
spans = defaultdict(list)
for i, r in enumerate(new_sec2):
    spans[r["team_id"]].append(i)
broken = [t for t, idxs in spans.items() if idxs != list(range(idxs[0], idxs[0]+len(idxs)))]
print(f"non-contiguous teams after insert: {len(broken)}")
t20030 = [r for r in new_sec2 if r["team_id"] == TEST_TEAM]
print(f"team {TEST_TEAM} records now: {len(t20030)}, last = {t20030[-1]}")

# --- Rebuild bundle ---
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
            d.save(); modified += 1
        elif name == 'ClubPlayer':
            d.m_Script = new_clubplayer_raw.decode('utf-8', errors='surrogateescape')
            d.save(); modified += 1
with open(BUNDLE_DST, 'wb') as f:
    f.write(env2.file.save())
print(f"Bundle written: {os.path.getsize(BUNDLE_DST):,} bytes (modified {modified} assets)")

# --- APK ---
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

print(f"\nDONE v7: pid={TEST_PID}, team={TEST_TEAM}, insert_pos={insert_pos}, f1=99, tail16={tmpl['tail16']}, fc={tmpl['fc']}")
