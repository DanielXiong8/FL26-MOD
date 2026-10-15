# Phase 13B - min3: three-way discriminator for the invisible-player root cause.
# Exp R1: REUSE existing generated pid 175900 ("Tilkowskl"): rename + PA swap + move
#         his ClubPlayer sec2 record from 10908 to Man City. Tests band-slot reuse.
# Exp N1: NEW pid 175899 inserted in SORTED position (physically just before 175900).
#         Tests normal-range pid with sorted insert.
# Exp N2: NEW pid 174500 APPENDED at physical end (after 175923, sort violation).
#         Tests whether end-append after the user band is the killer.
import io, os, shutil, struct, subprocess, zipfile
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
SRC_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_e2e.unity3d')
DST_GAMEDATA = os.path.join(ROOT, r'modified\gamedata_phase13b_min3.unity3d')
SRC_APK      = os.path.join(ROOT, r'dist\fl26_e2e.apk')
DST_APK      = os.path.join(ROOT, r'dist\fl26_phase13b_min3.apk')

MC, CHN, TEMPLATE_PID, REUSE_PID = 20026, 10059, 101351, 175900
P_R1, P_N1, P_N2 = 175900, 175899, 174500

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

# ---- Exp R1: rewrite the EXISTING 175900 record in place ----
r1 = next(r for r in recs if r['pid'] == REUSE_PID)
print('[R1] original: %s attrs[0]=%d' % (r1['name'], r1['attrs'][0]))
r1['name'] = 'P13B_R1'
r1['fa'], r1['fb'], r1['fc'], r1['nat'] = tmpl['fa'], tmpl['fb'], tmpl['fc'], tmpl['nat']
r1['attrs'] = list(range(81, 98))
r1['year'] = 1998

# ---- Exp N1: new record 175899, inserted just before the 1759xx band ----
n1 = dict(tmpl); n1['pid'] = P_N1; n1['name'] = 'P13B_N1'; n1['attrs'] = list(range(81, 98)); n1['year'] = 1998
idx_175900 = next(i for i, r in enumerate(recs) if r['pid'] == REUSE_PID)
recs.insert(idx_175900, n1)   # sorted position (table is ascending)
# ---- Exp N2: new record 174500 appended at physical end ----
n2 = dict(tmpl); n2['pid'] = P_N2; n2['name'] = 'P13B_N2'; n2['attrs'] = list(range(81, 98)); n2['year'] = 1998
recs.append(n2)
players_raw = serialize_plyrcsv0(nations, recs)
print('[Players] %d -> %d' % (52641, len(recs)))

# ---- ClubPlayer ----
cp = assets['ClubPlayer']
n1c = struct.unpack_from('<I', cp, 0)[0]
sec1 = [list(struct.unpack_from('<II', cp, 4 + i*8)) for i in range(n1c)]
sec2 = []
off = 4 + n1c*8
while off + 17 <= len(cp):
    tid, pid, f1, f2 = struct.unpack_from('<IIII', cp, off)
    sec2.append({'team_id': tid, 'player_id': pid, 'f1': f1, 'f2': f2, 'f3': cp[off+16]})
    off += 17
moved = False
for e in sec2:
    if e['player_id'] == P_R1 and e['team_id'] == 10908:
        e['team_id'] = MC; e['f1'] = 2; e['f2'] = 6912
        moved = True
print('[R1] sec2 record moved 10908->20026:', moved)
sec2.append({'team_id': MC, 'player_id': P_N1, 'f1': 3, 'f2': 6912, 'f3': 0})
sec2.append({'team_id': MC, 'player_id': P_N2, 'f1': 4, 'f2': 6912, 'f3': 0})
out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack('<II', tid, cnt))
for r in sec2:
    out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()
# bump Man City count by 3 (R1 moved in + N1 + N2)
for e in sec1:
    if e[0] == MC:
        e[1] += 3
        print('[ClubPlayer] 20026 count ->', e[1])
# re-serialize sec1 with updated count
out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1:
    out.write(struct.pack('<II', tid, cnt))
for r in sec2:
    out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()

# ---- PA: replace 175900's 17 bytes; append for 175899 + 174500 ----
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from('<I', pa, 0)[0]
idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
idx_map = dict(idx)
data = pa[4 + n*8:]
t_off = idx_map[TEMPLATE_PID]
t_app = bytes(pa[t_off+4:t_off+21])
# replace R1's PA record in place: its offset points into data blob
r1_off = idx_map[P_R1]
data = bytearray(data)
rel = r1_off - (4 + n*8)
data[rel+4:rel+21] = t_app
data = bytes(data)
new_pids = [P_N1, P_N2]
k = len(new_pids)
new_n = n + k
base = 4 + new_n*8 + len(data)
out2 = io.BytesIO()
out2.write(struct.pack('<I', new_n))
for kk, oo in idx:
    out2.write(struct.pack('<II', kk, oo + 8*k))
for j, pid in enumerate(new_pids):
    out2.write(struct.pack('<II', pid, base + j*21))
out2.write(data)
for j, pid in enumerate(new_pids):
    out2.write(struct.pack('<I', pid) + t_app)
pa_raw = out2.getvalue()
print('[PA] %d -> %d (R1 bytes replaced in place)' % (n, new_n))

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
