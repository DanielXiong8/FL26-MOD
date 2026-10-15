# -*- coding: utf-8 -*-
"""Step 11 E2E injection (final, arsenal_v3-proven style).

Base  : dist/fl26_allchina_v5.apk  (the mod on the device)
Change: inject ONE new static player into gamedata:
        Players  : append pid 175923 "Ma Jiantao" (fa/fb/fc=0, b1=3 FW, attrs 81..97)
        ClubPlayer: team 20026 (Manchester City) sec1 count+1, the new record at the
                    PHYSICAL END of sec2 with f1=1 (highest priority) -- the exact
                    proven arsenal_v3 approach that showed CustomeagueTest on device.
Output: dist/fl26_e2e.apk (zipaligned + signed)
"""
import struct, sys, io, os, shutil, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

ROOT = r'D:\FL26_Mod'
BASE_APK = ROOT + r'\dist\fl26_allchina_v5.apk'
GAMEDATA_EXTRACT = ROOT + r'\build\e2e_gamedata_src.unity3d'
BUNDLE_DST = ROOT + r'\modified\gamedata_e2e.unity3d'

TEST_PID = 175923
TEST_NAME = "Ma Jiantao"
TEST_ATTRS = list(range(81, 98))
TEST_TEAM = 20026  # Manchester City
TEST_YEAR = 1998

# Optional build config (Phase 12 Dashboard orchestration): a JSON file overriding
# the player parameters without touching this proven script. Absent = the defaults.
_CFG = os.environ.get('PHASE11_CONFIG')
if _CFG and os.path.exists(_CFG):
    import json as _json
    cfg = _json.load(open(_CFG, encoding='utf-8'))
    TEST_PID = int(cfg.get('pid', TEST_PID))
    TEST_NAME = cfg.get('name', TEST_NAME)
    TEST_TEAM = int(cfg.get('team_id', TEST_TEAM))
    TEST_ATTRS = list(cfg.get('attrs', TEST_ATTRS))
    TEST_YEAR = int(cfg.get('year', TEST_YEAR))
    print('[config] override loaded: pid=%d name=%s team=%d' % (TEST_PID, TEST_NAME, TEST_TEAM))
APPEARANCE_CLONE_PID = 101351  # Yang J. (10059 f1=1, PA b1=14/b14=17)

BT = ROOT + r'\android-sdk\build-tools\36.0.0'
ZIPALIGN = BT + r'\zipalign.exe'
APKSIGNER = BT + r'\apksigner.bat'
KEYSTORE = ROOT + r'\build\fl26_test.keystore'
DST_APK = ROOT + r'\dist\fl26_e2e.apk'

if not os.path.exists(GAMEDATA_EXTRACT) or os.environ.get('FORCE_EXTRACT'):
    with zipfile.ZipFile(BASE_APK) as z:
        z.extract('assets/bundles/gamedata.unity3d', os.path.dirname(GAMEDATA_EXTRACT))
    shutil.move(os.path.join(os.path.dirname(GAMEDATA_EXTRACT), 'assets/bundles/gamedata.unity3d'), GAMEDATA_EXTRACT)
print('[base] gamedata ready')

env = UnityPy.load(GAMEDATA_EXTRACT)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        if name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            raw = d.m_Script
            assets[name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

def parse_plyrcsv0(raw):
    off = 8
    ncnt = struct.unpack_from('<H', raw, off)[0]; off += 2
    nations = []
    for _ in range(ncnt):
        ln = struct.unpack_from('<H', raw, off)[0]; off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    pcnt = struct.unpack_from('<I', raw, off)[0]; off += 4
    recs = []
    for i in range(pcnt):
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
    out.write(b'plyrcsv0')
    out.write(struct.pack('<H', len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le')
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

nations, recs = parse_plyrcsv0(assets['Players'])
# appearance template: Onahi (100612) -- a CHN teammate; his Players-table
# fa/fb/fc = the eastAsia head-model codes and his PA record pairs the
# face_eastAsia_new1 texture (our fresh Ma Jiantao bake) with the
# face_EastAsia_new1 head mesh (our injected MICA verts)
TEMPLATE_PID = 101351  # Yang J.
tmpl = next(r for r in recs if r['pid'] == TEMPLATE_PID)
print('[template] Onahi: fa=%d fb=%d fc=%d nat=%d' % (tmpl['fa'], tmpl['fb'], tmpl['fc'], tmpl['nat']))
new_player = {
    'pid': TEST_PID, 'name': TEST_NAME,
    'fa': tmpl['fa'], 'fb': tmpl['fb'], 'fc': tmpl['fc'], 'nat': tmpl['nat'],
    'b1': tmpl['b1'], 'b16': tmpl['b16'], 'b0': tmpl['b0'],
    'attrs': TEST_ATTRS,
    'tail16': tmpl['tail16'], 'tail8': tmpl['tail8'], 'year': tmpl['year'],
}
new_players_raw = serialize_plyrcsv0(nations, recs + [new_player])
print('[Players] pid %d appended (%d -> %d), nat=13, b1=3(FW), fa/fb/fc=0' % (TEST_PID, len(recs), len(recs)+1))

raw = assets['ClubPlayer']
n1 = struct.unpack_from('<I', raw, 0)[0]
sec1 = [list(struct.unpack_from('<II', raw, 4 + i*8)) for i in range(n1)]
sec2 = []
off = 4 + n1*8
while off + 17 <= len(raw):
    tid, pid, f1, f2 = struct.unpack_from('<IIII', raw, off)
    sec2.append({'team_id': tid, 'player_id': pid, 'f1': f1, 'f2': f2, 'f3': raw[off+16]})
    off += 17
for e in sec1:
    if e[0] == TEST_TEAM:
        e[1] += 1
        print('[ClubPlayer] team %d count %d -> %d' % (TEST_TEAM, e[1]-1, e[1]))
new_rec = {'team_id': TEST_TEAM, 'player_id': TEST_PID, 'f1': 1, 'f2': 6912, 'f3': 0}
new_sec2 = sec2 + [new_rec]
out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack('<II', tid, cnt))
for r in new_sec2:
    out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
    out.write(bytes([r['f3']]))
new_clubplayer_raw = out.getvalue()

# ---------- PlayerAppearanceTable: append 175923 cloning Onahi's record ----------
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from('<I', pa, 0)[0]
idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
idx_map = dict(idx)
data_start = 4 + n*8
data = pa[data_start:]
t_off = idx_map[TEMPLATE_PID]
t_rec = pa[t_off:t_off+21]
app = bytearray(t_rec[4:])
print('[Appearance] clone Onahi: b1=%d b4=%d b7=%d b10=%d b14=%d' % (app[1], app[4], app[7], app[10], app[14]))
new_app_rec = struct.pack('<I', TEST_PID) + bytes(app)
new_n = n + 1
new_rec_off = 4 + new_n*8 + len(data)
out2 = io.BytesIO()
out2.write(struct.pack('<I', new_n))
for k, o in idx:
    out2.write(struct.pack('<II', k, o + 8))
out2.write(struct.pack('<II', TEST_PID, new_rec_off))
out2.write(data)
out2.write(new_app_rec)
new_pa = out2.getvalue()
print('[Appearance] entries %d -> %d' % (n, new_n))
print('[ClubPlayer] sec2 %d -> %d (f1=1 highest priority, physical-end append)' % (len(sec2), len(new_sec2)))

shutil.copyfile(GAMEDATA_EXTRACT, BUNDLE_DST)
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
print('[bundle] rebuilt, TextAssets modified: %d' % modified)

with zipfile.ZipFile(BASE_APK, 'r') as zin:
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
if os.path.exists(aligned): os.replace(aligned, DST_APK)
r = subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE, '--ks-pass', 'pass:fl26modtest',
                    '--ks-key-alias', 'fl26test', DST_APK], capture_output=True, text=True, env=env_vars)
print('sign:', 'OK' if r.returncode == 0 else r.stderr[-300:])
v = subprocess.run([APKSIGNER, 'verify', DST_APK], capture_output=True, text=True, env=env_vars)
print('verify:', 'OK' if v.returncode == 0 else v.stdout[-200:])
print('DONE: ' + DST_APK)
