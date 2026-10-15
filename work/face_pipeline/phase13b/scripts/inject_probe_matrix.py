# Phase 13B - Probe Matrix Injector
# Appends 18 probe players to team 10059 (China NT) in the CURRENT PROVEN baseline
# (dist/fl26_e2e.apk gamedata), each isolating ONE appearance byte on top of the
# device-verified Yang J. (101351) appearance clone. Read-only w.r.t. protected assets:
# reads modified/gamedata_e2e.unity3d, writes a NEW file; APK written to a NEW name.
import io, os, shutil, struct, subprocess, zipfile
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
SRC_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_e2e.unity3d')   # proven baseline (Ma Jiantao @ 20026)
DST_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_phase13b.unity3d')
SRC_APK      = os.path.join(ROOT, r'dist\fl26_e2e.apk')               # proven visible-face baseline
_apk_name = os.environ.get('PHASE13B_APK', 'fl26_phase13b_probe.apk')
DST_APK      = os.path.join(ROOT, 'dist', _apk_name)

TEAM = 10059          # China NT (verified reachable in squad UI)
TEMPLATE_PID = 101351 # Yang J. - device-verified eastAsia appearance clone source
FIRST_PID = 175924    # right after 175923 (last used high pid)

# PA base = Yang J.: b0=6 b1=14 b3=16 b4=0 b5=2 b6=1 b7=0 b8=1 b14=17 b16=127
# Each probe overrides ONLY the listed byte offsets (PA byte index -> value).
# PHASE13B_ONLY: comma-separated probe names to include (roster-cap debugging);
# absent = full 18-probe matrix.
import os as _os
_ONLY = _os.environ.get('PHASE13B_ONLY')
ALL_PROBES = [
    ('P13B_P00', {}),                    # exact Yang J. clone (control)
    ('P13B_P01', {3: 1}),                # hair index 1
    ('P13B_P02', {3: 2}),                # hair index 2
    ('P13B_P03', {3: 3}),                # hair index 3
    ('P13B_P04', {5: 0}),                # hair color 0 (0x6D3F02)
    ('P13B_P05', {5: 5}),                # hair color 5 (0xB0787B reddish)
    ('P13B_P06', {5: 6}),                # hair color 6 (0xB0C4DE light)
    ('P13B_P07', {8: 3}),                # eyebrow style 3
    ('P13B_P08', {8: 6}),                # eyebrow style 6
    ('P13B_P09', {7: 127, 8: 127}),      # beard OFF (sentinel)
    ('P13B_P10', {6: 5}),                # beard style Beard5
    ('P13B_P11', {6: 8}),                # beard style Beard8 (mustache, device-confirmed)
    ('P13B_P12', {14: 0}),               # face shape template 0
    ('P13B_P13', {14: 42}),              # face shape template 42
    ('P13B_P14', {14: 99}),              # face shape template 99
    ('P13B_P15', {0: 1}),                # skin tone 1
    ('P13B_P16', {0: 7}),                # skin tone 7
    ('P13B_P17', {10: 7}),               # b10 flag 7 (generated-player value)
]
if _ONLY:
    _keep = set(_ONLY.split(','))
    PROBES = [p for p in ALL_PROBES if p[0] in _keep]
    print('[subset] %d probes: %s' % (len(PROBES), [p[0] for p in PROBES]))
else:
    PROBES = ALL_PROBES

# ---------- parse helpers (verbatim patterns from proven phase11 injector) ----------
def parse_plyrcsv0(raw):
    off = 8
    ncnt = struct.unpack_from('<H', raw, off)[0]; off += 2
    nations = []
    for _ in range(ncnt):
        ln = struct.unpack_from('<H', raw, off)[0]; off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    pcnt = struct.unpack_from('<I', raw, off)[0]; off += 4
    recs = []
    for _ in range(pcnt):
        pid = struct.unpack_from('<I', raw, off)[0]; off += 4
        ln = struct.unpack_from('<H', raw, off)[0]; off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from('<HHHH', raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16 = struct.unpack_from('<H', raw, off)[0]; off += 2
        tail8 = raw[off]; off += 1
        year = struct.unpack_from('<I', raw, off)[0]; off += 4
        recs.append({'pid': pid, 'name': name, 'fa': fa, 'fb': fb, 'fc': fc, 'nat': nat,
                     'b1': b1, 'b16': b16, 'b0': b0, 'attrs': attrs,
                     'tail16': tail16, 'tail8': tail8, 'year': year})
    return nations, recs

def serialize_plyrcsv0(nations, recs):
    out = io.BytesIO()
    out.write(b'plyrcsv0')  # table magic (the 8 skipped header bytes)
    out.write(struct.pack('<H', len(nations)))
    for nat in nations:
        nb = nat.encode('utf-16-le', errors='replace')
        out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
    out.write(struct.pack('<I', len(recs)))
    for r in recs:
        out.write(struct.pack('<I', r['pid']))
        nb = r['name'].encode('utf-16-le', errors='replace')
        out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
        out.write(struct.pack('<HHHH', r['fa'], r['fb'], r['fc'], r['nat']))
        out.write(bytes([r['b1'], r['b16'], r['b0']]))
        out.write(bytes(r['attrs']))
        out.write(struct.pack('<H', r['tail16']))
        out.write(bytes([r['tail8']]))
        out.write(struct.pack('<I', r['year']))
    return out.getvalue()

env = UnityPy.load(SRC_GAMEDATA)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            raw = d.m_Script
            assets[d.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
print('[load] Players=%d ClubPlayer=%d PA=%d' % (len(assets['Players']), len(assets['ClubPlayer']), len(assets['PlayerAppearanceTable'])))

nations, recs = parse_plyrcsv0(assets['Players'])
tmpl = next(r for r in recs if r['pid'] == TEMPLATE_PID)
print('[template] Yang J.: fa=%d fb=%d fc=%d nat=%d b1=%d b16=%d b0=%d' % (
    tmpl['fa'], tmpl['fb'], tmpl['fc'], tmpl['nat'], tmpl['b1'], tmpl['b16'], tmpl['b0']))

# guard: target pids free
used = {r['pid'] for r in recs}
assert not any(FIRST_PID + i in used for i in range(len(PROBES))), 'pid collision'

new_players = []
for i, (name, _) in enumerate(PROBES):
    p = dict(tmpl)
    p['pid'] = FIRST_PID + i
    p['name'] = name
    # Position classification comes from the 17-attr profile, not Players.b1.
    # Yang J. is a GK: cloning his attrs made all probes GKs -> invisible in the
    # squad UI (only 1-2 GK slots). Use the device-proven visible FW attr profile.
    p['attrs'] = list(range(81, 98))
    new_players.append(p)
players_raw = serialize_plyrcsv0(nations, recs + new_players)
print('[Players] %d -> %d' % (len(recs), len(recs) + len(new_players)))

# ---------- ClubPlayer ----------
cp = assets['ClubPlayer']
n1 = struct.unpack_from('<I', cp, 0)[0]
sec1 = [list(struct.unpack_from('<II', cp, 4 + i*8)) for i in range(n1)]
sec2 = []
off = 4 + n1*8
while off + 17 <= len(cp):
    tid, pid, f1, f2 = struct.unpack_from('<IIII', cp, off)
    sec2.append({'team_id': tid, 'player_id': pid, 'f1': f1, 'f2': f2, 'f3': cp[off+16]})
    off += 17
for e in sec1:
    if e[0] == TEAM:
        e[1] += len(PROBES)
        print('[ClubPlayer] team %d count %d -> %d' % (TEAM, e[1]-len(PROBES), e[1]))
# f1 = jersey number (must be unique per team: China originals use 1-25; 30+ free)
new_sec2 = sec2 + [{'team_id': TEAM, 'player_id': FIRST_PID + i, 'f1': 30 + i, 'f2': 6912, 'f3': 0}
                   for i in range(len(PROBES))]
out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack('<II', tid, cnt))
for r in new_sec2:
    out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()

# ---------- PlayerAppearanceTable ----------
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from('<I', pa, 0)[0]
idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
idx_map = dict(idx)
data = pa[4 + n*8:]
t_off = idx_map[TEMPLATE_PID]
t_app = bytearray(pa[t_off+4:t_off+21])
print('[PA template] Yang J. bytes:', list(t_app))
new_pa_recs = []
for i, (name, overrides) in enumerate(PROBES):
    app = bytearray(t_app)
    for k, v in overrides.items():
        app[k] = v
    new_pa_recs.append(struct.pack('<I', FIRST_PID + i) + bytes(app))
new_n = n + len(PROBES)
new_rec_off = 4 + new_n*8 + len(data)
out2 = io.BytesIO()
out2.write(struct.pack('<I', new_n))
for k, o in idx:
    out2.write(struct.pack('<II', k, o + 8*len(PROBES)))
for j, rec in enumerate(new_pa_recs):
    out2.write(struct.pack('<II', FIRST_PID + j, new_rec_off + j*21))
out2.write(data)
for rec in new_pa_recs:
    out2.write(rec)
pa_raw = out2.getvalue()
print('[PA] %d -> %d' % (n, new_n))

# ---------- rebuild bundle ----------
shutil.copyfile(SRC_GAMEDATA, DST_GAMEDATA)
env2 = UnityPy.load(DST_GAMEDATA)
payloads = {'Players': players_raw, 'ClubPlayer': clubplayer_raw, 'PlayerAppearanceTable': pa_raw}
modified = 0
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in payloads:
            d.m_Script = payloads[d.m_Name].decode('utf-8', errors='surrogateescape')
            d.save(); modified += 1
with open(DST_GAMEDATA, 'wb') as f:
    f.write(env2.file.save())
print('[bundle] rebuilt, TextAssets modified: %d' % modified)

# ---------- repack APK ----------
with zipfile.ZipFile(SRC_APK, 'r') as zin:
    with zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/gamedata.unity3d':
                with open(DST_GAMEDATA, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(DST_APK + '.tmp', DST_APK)

BT = os.path.join(ROOT, 'android-sdk', 'build-tools', '36.0.0')
env_vars = dict(os.environ)
JH = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['JAVA_HOME'] = JH
env_vars['Path'] = JH + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
if os.path.exists(aligned): os.replace(aligned, DST_APK)
r = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', os.path.join(ROOT, r'build\fl26_test.keystore'),
                    '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', DST_APK],
                   capture_output=True, text=True, env=env_vars)
print('sign:', 'OK' if r.returncode == 0 else r.stderr[-300:])
v = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'verify', DST_APK], capture_output=True, text=True, env=env_vars)
print('verify:', 'OK' if v.returncode == 0 else v.stdout[-200:])
print('DONE: ' + DST_APK)
