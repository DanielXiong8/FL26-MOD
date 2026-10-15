# -*- coding: utf-8 -*-
"""
Step 8 Track A: Appearance Differential Experiment build.
Builds appearance_diff_v1.apk with 13 test players in London Red (20030):
  baseline: pid 175923 "CustomAppearanceTest" (Ralla appearance clone, unchanged)
  T01-T12 : pid 175924-175935, each with ONE appearance byte changed

Value adjustments vs spec (documented):
  - Byte 4/7 observed values are only {0, 127}; spec's "1" tested blind as T05/T07,
    observed on-value 127 added as T06/T08.
  - Byte 10 observed values are {0, 7}; spec's "1" tested blind as T09,
    observed nonzero 7 added as T10.

Outputs:
  dist/appearance_diff_v1.apk  (built, signed, installed, data cleared)
  recon/03_player/appearance_diff/baseline.json, T01.json ... T12.json
"""
import struct, sys, io, os, json, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

TEST_TEAM = 20030
TEMPLATE_PID = 103346  # Ralla
BASELINE_PID = 175923
BASELINE_NAME = "CustomAppearanceTest"
BASE_JERSEY = 99
T_JERSEY_START = 70  # 70..81 for T01..T12 (20030 uses 1-56, 99)

# Ralla appearance 17B baseline
BASELINE_APP = bytes([0x01, 0x1e, 0x00, 0x13, 0x00, 0x02, 0x17, 0x00, 0x01, 0x7f,
                      0x00, 0x00, 0x00, 0x00, 0x2a, 0x00, 0x7f])

# 12 experiments: (test_id, byte_index, old_value, new_value)
EXPERIMENTS = [
    ("T01", 0,  0x01, 0x02),
    ("T02", 0,  0x01, 0x03),
    ("T03", 1,  0x1e, 0x1f),   # 30 -> 31
    ("T04", 1,  0x1e, 0x20),   # 30 -> 32
    ("T05", 4,  0x00, 0x01),   # blind (spec)
    ("T06", 4,  0x00, 0x7f),   # observed on-value
    ("T07", 7,  0x00, 0x01),   # blind (spec)
    ("T08", 7,  0x00, 0x7f),   # observed on-value
    ("T09", 10, 0x00, 0x01),   # blind (spec)
    ("T10", 10, 0x00, 0x07),   # observed nonzero
    ("T11", 14, 0x2a, 0x2b),   # 42 -> 43
    ("T12", 14, 0x2a, 0x2c),   # 42 -> 44
]

BUNDLE_SRC = r'C:\FL26_Mod\build\gamedata.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_appearance_diff_v1.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\appearance_diff_v1.apk'
DIFF_DIR = r'C:\FL26_Mod\recon\03_player\appearance_diff'
os.makedirs(DIFF_DIR, exist_ok=True)

# ---------------- parse helpers (from validated phase4a_v9 chain) ----------------
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

# ---------------- load bundle ----------------
env = UnityPy.load(BUNDLE_SRC)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            raw = d.m_Script
            assets[d.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

# ---------------- Players: append 13 ----------------
nations, recs = parse_plyrcsv0(assets['Players'])
tmpl = next(r for r in recs if r["pid"] == TEMPLATE_PID)

def make_player(pid, name, jersey):
    return {"pid": pid, "name": name, "fa": tmpl["fa"], "fb": tmpl["fb"], "fc": tmpl["fc"],
            "nat": tmpl["nat"], "b1": 14, "b16": tmpl["b16"], "b0": tmpl["b0"],
            "attrs": tmpl["attrs"], "tail16": tmpl["tail16"], "tail8": tmpl["tail8"], "year": 1998}

new_players = [make_player(BASELINE_PID, BASELINE_NAME, BASE_JERSEY)]
for i, (tid, _, _, _) in enumerate(EXPERIMENTS):
    new_players.append(make_player(BASELINE_PID + 1 + i, tid, T_JERSEY_START + i))

new_players_raw = serialize_plyrcsv0(nations, recs + new_players)
print(f"[Players] +{len(new_players)} (52640 -> {len(recs)+len(new_players)})")

# ---------------- PlayerAppearanceTable: append 13 ----------------
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
idx_entries = [struct.unpack_from("<II", pa, 4 + i*8) for i in range(n)]
data_start = 4 + n*8
data = pa[data_start:]
t_off = dict(idx_entries)[TEMPLATE_PID]
t_rec = pa[t_off:t_off+21]  # pid(4) + 17B appearance
assert t_rec[4:] == BASELINE_APP, f"template mismatch: {t_rec[4:].hex()}"

app_records = [(BASELINE_PID, BASELINE_APP)]
for i, (tid, bi, old, new) in enumerate(EXPERIMENTS):
    mod = bytearray(BASELINE_APP)
    assert mod[bi] == old, f"{tid}: baseline byte {bi} = {mod[bi]:02x}, expected {old:02x}"
    mod[bi] = new
    app_records.append((BASELINE_PID + 1 + i, bytes(mod)))

new_n = n + len(app_records)
shift = 8 * len(app_records)
new_data_start = 4 + new_n*8
out = io.BytesIO()
out.write(struct.pack("<I", new_n))
for k, o in idx_entries:
    out.write(struct.pack("<II", k, o + shift))
cursor = new_data_start + len(data)
for pid, app in app_records:
    out.write(struct.pack("<II", pid, cursor))
    cursor += 21
out.write(data)
for pid, app in app_records:
    out.write(struct.pack("<I", pid)); out.write(app)
new_pa = out.getvalue()
print(f"[Appearance] +{len(app_records)} entries ({n} -> {new_n})")

# ---------------- ClubPlayer: insert 13 after 20030 block ----------------
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
        e[1] += len(app_records)  # 24 -> 37

new_recs = [{"team_id": TEST_TEAM, "player_id": BASELINE_PID, "f1": BASE_JERSEY, "f2": 6912, "f3": 0}]
for i, (tid, _, _, _) in enumerate(EXPERIMENTS):
    new_recs.append({"team_id": TEST_TEAM, "player_id": BASELINE_PID + 1 + i,
                     "f1": T_JERSEY_START + i, "f2": 6912, "f3": 0})
new_sec2 = sec2[:insert_pos] + new_recs + sec2[insert_pos:]

out = io.BytesIO()
out.write(struct.pack("<I", len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack("<II", tid, cnt))
for r in new_sec2:
    out.write(struct.pack("<IIII", r["team_id"], r["player_id"], r["f1"], r["f2"]))
    out.write(bytes([r["f3"]]))
new_club = out.getvalue()
print(f"[ClubPlayer] +{len(new_recs)} @ {insert_pos} (sec2 {len(sec2)} -> {len(new_sec2)})")

# ---------------- rebuild bundle ----------------
shutil.copy2(BUNDLE_SRC, BUNDLE_DST)
env2 = UnityPy.load(BUNDLE_DST)
payloads = {'Players': new_players_raw, 'ClubPlayer': new_club, 'PlayerAppearanceTable': new_pa}
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in payloads:
            d.m_Script = payloads[d.m_Name].decode('utf-8', errors='surrogateescape')
            d.save()
with open(BUNDLE_DST, 'wb') as f:
    f.write(env2.file.save())

# ---------------- APK ----------------
with zipfile.ZipFile(SRC_APK, 'r') as zin:
    with zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/gamedata.unity3d':
                with open(BUNDLE_DST, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(DST_APK + '.tmp', DST_APK)

BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
os.replace(aligned, DST_APK)
r = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', r'C:\FL26_Mod\build\fl26_test.keystore',
                    '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', DST_APK],
                   capture_output=True, text=True, env=env_vars)
print("sign:", 'OK' if r.returncode == 0 else r.stderr[-300:])

# ---------------- experiment JSONs ----------------
def dump(name, pid, field, old, new, baseline, modified, note=""):
    with open(os.path.join(DIFF_DIR, f'{name}.json'), 'w', encoding='utf-8') as f:
        json.dump({
            "test_id": name, "pid": pid, "team": TEST_TEAM, "jersey": T_JERSEY_START + (int(name[1:]) - 1) if name != "baseline" else BASE_JERSEY,
            "field": f"byte_{field}", "old_value": old, "new_value": new,
            "baseline_bytes": baseline.hex(), "modified_bytes": modified.hex(),
            "visible_change": None, "change_type": None, "confidence": None, "note": note,
        }, f, indent=2, ensure_ascii=False)

dump("baseline", BASELINE_PID, None, None, None, BASELINE_APP, BASELINE_APP, "control: pure Ralla clone")
for i, (tid, bi, old, new) in enumerate(EXPERIMENTS):
    mod = bytearray(BASELINE_APP); mod[bi] = new
    note = "blind value (not observed in 52646 records)" if new in (0x01,) and bi in (4, 7, 10) else ""
    dump(tid, BASELINE_PID + 1 + i, bi, old, new, BASELINE_APP, bytes(mod), note)

print(f"\nexperiment JSONs -> {DIFF_DIR}")

# ---------------- install + clear ----------------
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
r = subprocess.run([ADB, 'install', '-r', DST_APK], capture_output=True, text=True, timeout=180)
print("install:", (r.stdout.strip() or r.stderr.strip())[:200])
r = subprocess.run([ADB, 'shell', 'pm', 'clear', 'com.football.soccer.league.mod'], capture_output=True, text=True, timeout=60)
print("pm clear:", r.stdout.strip())
print("\nDONE appearance_diff_v1")
