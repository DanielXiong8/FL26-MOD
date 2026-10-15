# -*- coding: utf-8 -*-
# build_b14_matrix.py - avatar(baked_ea2) + gamedata(Ralla patch + 10 b14 test players) -> APK -> install
import struct, io, os, shutil, zipfile, subprocess
import numpy as np
from PIL import Image
import UnityPy

TEAM = 20030
PIDS = list(range(175950, 175960))          # 10 test players
B14S = [37, 38, 39, 40, 41, 43, 44, 45, 46, 47]  # one per player; 42=control
Jerseys = list(range(70, 80))
APP = bytes([0x01, 0x16, 0x00, 0x13, 0x00, 0x02, 0x17, 0x7f, 0x01, 0x7f,
             0x00, 0x00, 0x00, 0x00, 0x2a, 0x00, 0x7f])  # b1=22, b7=127

GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_b14matrix.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

# ---------- avatar ----------
TARGET = "assets/models/player2021/textures/face/face_eastasia_new1.png"
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
tex = env.container[TARGET].read()
img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea2.png').convert('RGB')
tex.set_image(img); tex.save()
AV = r'C:\FL26_Mod\build\avatar_ea2_baked.unity3d'
open(AV,'wb').write(env.file.save(packer='original'))
env2 = UnityPy.load(AV)
d = np.abs(np.array(env2.container[TARGET].read().image.convert('RGB'),np.float32)-np.array(img,np.float32)).mean()
print('avatar inject diff %.2f' % d)

# ---------- gamedata ----------
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
    out.write(b"plyrcsv0"); out.write(struct.pack("<H", len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le'); out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
    out.write(struct.pack("<I", len(recs)))
    for r in recs:
        out.write(struct.pack("<I", r["pid"]))
        nb = r["name"].encode('utf-16-le', errors='replace')
        out.write(struct.pack("<H", len(nb)//2)); out.write(nb)
        out.write(struct.pack("<HHHH", r["fa"], r["fb"], r["fc"], r["nat"]))
        out.write(bytes([r["b1"], r["b16"], r["b0"]]))
        out.write(bytes(r["attrs"]))
        out.write(struct.pack("<H", r["tail16"])); out.write(bytes([r["tail8"]]))
        out.write(struct.pack("<I", r["year"]))
    return out.getvalue()

g = UnityPy.load(GD)
assets = {}
for obj in g.objects:
    if obj.type.name == 'TextAsset':
        dd = obj.read(check_read=False)
        if dd.m_Name in ('Players','ClubPlayer','PlayerAppearanceTable'):
            raw = dd.m_Script
            assets[dd.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw,str) else bytes(raw)

# Players: append 10
nations, recs = parse_plyrcsv0(assets['Players'])
tmpl = next(r for r in recs if r["pid"] == 103346)
newp = []
for i,(pid,b14,jer) in enumerate(zip(PIDS,B14S,Jerseys)):
    app = bytearray(APP); app[14] = b14
    newp.append({"pid": pid, "name": "B14T%02d" % b14, "fa": tmpl["fa"], "fb": tmpl["fb"],
                 "fc": tmpl["fc"], "nat": tmpl["nat"], "b1": 14, "b16": tmpl["b16"],
                 "b0": tmpl["b0"], "attrs": list(app), "tail16": tmpl["tail16"],
                 "tail8": tmpl["tail8"], "year": 1998})
players_raw = serialize_plyrcsv0(nations, recs + newp)
print('[Players] +10')

# PlayerAppearanceTable: patch Ralla + append 10
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
idx_entries = [struct.unpack_from("<II", pa, 4+i*8) for i in range(n)]
# patch Ralla FIRST, then slice data
for k,o in idx_entries:
    if k == 103346:
        rec = bytearray(pa[o:o+21]); rec[4+1]=22; rec[4+7]=127
        pa = pa[:o] + bytes(rec) + pa[o+21:]
        print('[Appearance] Ralla patched:', rec[4:].hex())
        break
data = pa[4+n*8:]
app_recs = [(pid, bytes(bytearray(APP)[:14] + bytes([b14]) + bytearray(APP)[15:]))
            for pid,b14 in zip(PIDS,B14S)]
new_n = n + len(app_recs); shift = 8*len(app_recs)
out = io.BytesIO(); out.write(struct.pack("<I", new_n))
for k,o in idx_entries: out.write(struct.pack("<II", k, o+shift))
cursor = 4 + new_n*8 + len(data)
for pid,app in app_recs:
    out.write(struct.pack("<II", pid, cursor)); cursor += 21
out.write(data)
for pid,app in app_recs:
    out.write(struct.pack("<I", pid)); out.write(app)
pa_out = out.getvalue()
print('[Appearance] +%d test records' % len(app_recs))

# ClubPlayer: insert 10 into team 20030
raw = assets['ClubPlayer']
n1 = struct.unpack_from("<I", raw, 0)[0]
sec1 = [list(struct.unpack_from("<II", raw, 4+i*8)) for i in range(n1)]
sec2 = []; off = 4 + n1*8
while off + 17 <= len(raw):
    tid, pid, f1, f2 = struct.unpack_from("<IIII", raw, off)
    sec2.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": raw[off+16]})
    off += 17
rows = [i for i,r in enumerate(sec2) if r["team_id"] == TEAM]
pos = rows[-1]+1 if rows else len(sec2)
for e in sec1:
    if e[0] == TEAM: e[1] += len(newp)
ins = [{"team_id": TEAM, "player_id": pid, "f1": jer, "f2": 6912, "f3": 0}
       for pid,jer in zip(PIDS,Jerseys)]
sec2 = sec2[:pos] + ins + sec2[pos:]
out = io.BytesIO(); out.write(struct.pack("<I", len(sec1)))
for tid,cnt in sec1: out.write(struct.pack("<II", tid, cnt))
for r in sec2:
    out.write(struct.pack("<IIII", r["team_id"], r["player_id"], r["f1"], r["f2"]))
    out.write(bytes([r["f3"]]))
club = out.getvalue()
print('[ClubPlayer] +%d @%d' % (len(ins), pos))

# rebuild bundle
shutil.copy2(GD, GD_OUT)
g2 = UnityPy.load(GD_OUT)
payloads = {'Players': players_raw, 'ClubPlayer': club, 'PlayerAppearanceTable': pa_out}
for obj in g2.objects:
    if obj.type.name == 'TextAsset':
        dd = obj.read(check_read=False)
        if dd.m_Name in payloads:
            dd.m_Script = payloads[dd.m_Name].decode('utf-8', errors='surrogateescape'); dd.save()
with open(GD_OUT,'wb') as f:
    f.write(g2.file.save())
# verify roundtrip: Ralla record + test record count
import UnityPy as _U
import struct as _st
g3 = _U.load(GD_OUT)
for obj in g3.objects:
    if obj.type.name=='TextAsset':
        dd=obj.read(check_read=False)
        if dd.m_Name=='PlayerAppearanceTable':
            r2=dd.m_Script; r2=r2.encode('utf-8',errors='surrogateescape') if isinstance(r2,str) else bytes(r2)
            nn=_st.unpack_from('<I',r2,0)[0]
            for i in range(nn):
                k,o=_st.unpack_from('<II',r2,4+i*8)
                if k==103346: print('[verify] Ralla:', r2[o:o+21].hex())
                if k==PIDS[0]: print('[verify] T37  :', r2[o:o+21].hex())
            print('[verify] records:', nn)

# ---------- APK ----------
DST = r'C:\FL26_Mod\dist\fl26_b14matrix.apk'
with zipfile.ZipFile(SRC_APK) as zin, zipfile.ZipFile(DST+'.tmp','w') as zout:
    for it in zin.infolist():
        zout.writestr(it, open(GD_OUT,'rb').read() if it.filename=='assets/bundles/gamedata.unity3d'
                      else (open(AV,'rb').read() if it.filename=='assets/bundles/avatar.unity3d'
                            else zin.read(it.filename)))
shutil.move(DST+'.tmp', DST)
alg = DST.replace('.apk','_aligned.apk')
subprocess.run([BT+r'\zipalign.exe','-p','-f','4',DST,alg], check=True, env=envv)
os.replace(alg, DST)
r = subprocess.run([BT+r'\apksigner.bat','sign','--ks',r'C:\FL26_Mod\build\fl26_test.keystore',
    '--ks-pass','pass:fl26modtest','--out',DST,DST], capture_output=True, text=True, env=envv)
if r.returncode: print(r.stderr[-500:]); raise SystemExit(1)
r = subprocess.run([ADB,'install','-r',DST], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip())
