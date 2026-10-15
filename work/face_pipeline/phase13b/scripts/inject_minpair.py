# Phase 13B - minimal discriminator: 1 player @ Man City + 1 player @ China NT
import io, os, shutil, struct, subprocess, zipfile
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
SRC_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_e2e.unity3d')   # PRISTINE proven baseline (only Ma Jiantao)
DST_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_phase13b_min2.unity3d')
SRC_APK      = os.path.join(ROOT, r'dist\fl26_e2e.apk')
DST_APK      = os.path.join(ROOT, r'dist\fl26_phase13b_min2.apk')

MC, CHN, TEMPLATE_PID = 20026, 10059, 101351  # Yang J.
P_MC, P_CHN = 175942, 175943

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
    out.write(b'plyrcsv0')
    out.write(struct.pack('<H', len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le', errors='replace')
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

nations, recs = parse_plyrcsv0(assets['Players'])
tmpl = next(r for r in recs if r['pid'] == TEMPLATE_PID)
new = []
for pid, name, team in ((P_MC, 'P13B_MC1', MC), (P_CHN, 'P13B_CH1', CHN)):
    p = dict(tmpl); p['pid'] = pid; p['name'] = name; p['attrs'] = list(range(81, 98))
    new.append((p, team))
players_raw = serialize_plyrcsv0(nations, recs + [p for p, _ in new])
print('[Players] %d -> %d' % (len(recs), len(recs) + len(new)))

cp = assets['ClubPlayer']
n1 = struct.unpack_from('<I', cp, 0)[0]
sec1 = [list(struct.unpack_from('<II', cp, 4 + i*8)) for i in range(n1)]
sec2 = []
off = 4 + n1*8
while off + 17 <= len(cp):
    tid, pid, f1, f2 = struct.unpack_from('<IIII', cp, off)
    sec2.append({'team_id': tid, 'player_id': pid, 'f1': f1, 'f2': f2, 'f3': cp[off+16]})
    off += 17
jersey = {MC: 2, CHN: 30}
for e in sec1:
    for p, team in new:
        if e[0] == team:
            e[1] += 1
            print('[ClubPlayer] team %d count -> %d' % (team, e[1]))
for p, team in new:
    sec2.append({'team_id': team, 'player_id': p['pid'], 'f1': jersey[team], 'f2': 6912, 'f3': 0})
out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack('<II', tid, cnt))
for r in sec2:
    out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()

pa = assets['PlayerAppearanceTable']
n = struct.unpack_from('<I', pa, 0)[0]
idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
idx_map = dict(idx)
data = pa[4 + n*8:]
t_off = idx_map[TEMPLATE_PID]
t_app = bytearray(pa[t_off+4:t_off+21])
new_recs = [struct.pack('<I', p['pid']) + bytes(t_app) for p, _ in new]
k = len(new_recs)
new_n = n + k
base = 4 + new_n*8 + len(data)
out2 = io.BytesIO()
out2.write(struct.pack('<I', new_n))
for j, (kk, oo) in enumerate(idx):
    out2.write(struct.pack('<II', kk, oo + 8*k))
for j, rec in enumerate(new_recs):
    out2.write(struct.pack('<II', new[j][0]['pid'], base + j*21))
out2.write(data)
for rec in new_recs:
    out2.write(rec)
pa_raw = out2.getvalue()
print('[PA] %d -> %d' % (n, new_n))

shutil.copyfile(SRC_GAMEDATA, DST_GAMEDATA)
env2 = UnityPy.load(DST_GAMEDATA)
payloads = {'Players': players_raw, 'ClubPlayer': clubplayer_raw, 'PlayerAppearanceTable': pa_raw}
mod = 0
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in payloads:
            d.m_Script = payloads[d.m_Name].decode('utf-8', errors='surrogateescape')
            d.save(); mod += 1
with open(DST_GAMEDATA, 'wb') as f:
    f.write(env2.file.save())
print('[bundle] modified:', mod)

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
env_vars['JAVA_HOME'] = JH; env_vars['Path'] = JH + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
if os.path.exists(aligned): os.replace(aligned, DST_APK)
r = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', os.path.join(ROOT, r'build\fl26_test.keystore'),
                    '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', DST_APK], capture_output=True, text=True, env=env_vars)
print('sign:', 'OK' if r.returncode == 0 else r.stderr[-200:])
print('DONE: ' + DST_APK)
