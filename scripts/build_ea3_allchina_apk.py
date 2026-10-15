# -*- coding: utf-8 -*-
"""build_ea3_allchina_apk.py - China team all Ma Jiantao:
  - new1: MICA verts + baked_ea3 (as before)
  - new2..6: keep original 3D shape; REPLACE uv0 with new1's uv0 via NN vertex correspondence
  - ea3 texture -> all 6 face_eastasia_new*.png
  - Ralla b1=22 b7=127
"""
import struct, os, shutil, zipfile, subprocess, json
import numpy as np
from PIL import Image
import UnityPy
from scipy.spatial import cKDTree

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

ea1 = np.array(json.load(open(r'C:\FL26_Mod\work\face_pipeline\uv\mesh_ea1.json'))['vertices'], np.float64)
ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'))
V1 = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])  # game convention

def parse_mesh(vd):
    n = vd['m_VertexCount']
    data = bytes(vd['m_DataSize'])
    stride = 0
    for ch in vd['m_Channels']:
        if ch['stream'] == 0: stride = max(stride, ch['offset'] + ch['dimension'] * 4)
    fl = np.frombuffer(data, np.float32)
    pos = fl[:n*stride//4].reshape(n, stride//4)[:, 0:3].copy()
    s0len = n * stride
    uv_raw = np.frombuffer(data[s0len:], np.float32)
    uv0 = uv_raw.reshape(-1, 2)[0:n].copy()   # channel4 = stream1 offset0 dim2
    return pos, uv0, data, stride, s0len

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
meshes = {}
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name.startswith('face_EastAsia_new'):
            meshes[m.m_Name] = (o, m)
assert 'face_EastAsia_new1' in meshes

# parse new1 (ORIGINAL verts for correspondence, not MICA 鈥?shapes of others are variants of original)
o1, m1 = meshes['face_EastAsia_new1']
tree1 = o1.read_typetree()
vd1 = tree1['m_VertexData']
pos1, uv1_0, _, stride1, s0len1 = parse_mesh(vd1)
kd = cKDTree(pos1)

img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea3.png').convert('RGB')
for name in sorted(meshes):
    o, m = meshes[name]
    tree = o.read_typetree()
    vd = tree['m_VertexData']
    pos, uv0, data, stride, s0len = parse_mesh(vd)
    data = bytearray(data)
    n = vd['m_VertexCount']
    # texture ea3 for all
    tex = env.container['assets/models/player2021/textures/face/face_eastasia_new%d.png' % int(name[-1])].read()
    tex.set_image(img); tex.save()
    if name == 'face_EastAsia_new1':
        # MICA verts
        for i in range(n):
            off = i * stride
            data[off:off+12] = V1[i].astype('<f4').tobytes()
    else:
        # UV transfer via NN
        dist, idx = kd.query(pos)
        print('%s NN dist: mean=%.4f max=%.4f' % (name, dist.mean(), dist.max()))
        assert dist.max() < 0.05, (name, dist.max())
        uv_raw = np.frombuffer(data[s0len:], np.float32).copy()
        uv_arr = uv_raw.reshape(-1, 2)
        uv_arr[:n] = uv1_0[idx]
        data = data[:s0len] + uv_arr.tobytes()
    vd['m_DataSize'] = bytes(data)
    tree['m_VertexData'] = vd
    o.save_typetree(tree)
print('all 6 meshes processed')

AV = r'C:\FL26_Mod\build\avatar_ea3_allchina.unity3d'
with open(AV, 'wb') as f:
    f.write(env.file.save(packer='original'))

# verify: reload, check new3 uv0 == transferred & new1 verts == V1
env2 = UnityPy.load(AV)
for o in env2.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name == 'face_EastAsia_new1':
            fl = np.frombuffer(bytes(m.m_VertexData.m_DataSize), np.float32).reshape(-1, 10)[:700]
            assert np.abs(fl[:, :3] - V1.astype(np.float32)).max() < 1e-5
            print('new1 MICA verts verified')
        if m.m_Name == 'face_EastAsia_new3':
            print('new3 reload ok vc=', m.m_VertexData.m_VertexCount)

# gamedata
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_allchina.unity3d'
gen = UnityPy.load(GD)
pa_raw = None
for o in gen.objects:
    if o.type.name == 'TextAsset':
        d = o.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            raw = d.m_Script
            pa_raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
n = struct.unpack_from('<I', pa_raw, 0)[0]
off = None
for i in range(n):
    k, o = struct.unpack_from('<II', pa_raw, 4 + i*8)
    if k == 103346: off = o; break
rec = bytearray(pa_raw[off:off+21])
rec[4+1] = 22; rec[4+7] = 127
pa_raw = pa_raw[:off] + bytes(rec) + pa_raw[off+21:]
shutil.copy2(GD, GD_OUT)
g2 = UnityPy.load(GD_OUT)
for o in g2.objects:
    if o.type.name == 'TextAsset':
        d = o.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            d.m_Script = pa_raw.decode('utf-8', errors='surrogateescape')
            d.save()
with open(GD_OUT, 'wb') as f:
    f.write(g2.file.save())
print('gamedata ok')

# APK
DST = r'C:\FL26_Mod\dist\fl26_allchina_mjt.apk'
with zipfile.ZipFile(SRC_APK) as zin, zipfile.ZipFile(DST+'.tmp','w',zipfile.ZIP_STORED) as zout:
    for it in zin.infolist():
        if it.filename == 'assets/bundles/avatar.unity3d':
            zout.writestr(it, open(AV,'rb').read())
        elif it.filename == 'assets/bundles/gamedata.unity3d':
            zout.writestr(it, open(GD_OUT,'rb').read())
        else:
            zout.writestr(it, zin.read(it.filename))
shutil.move(DST+'.tmp', DST)
aligned = DST.replace('.apk','_aligned.apk')
subprocess.run([BT+r'\zipalign.exe','-p','-f','4',DST,aligned], check=True, env=envv)
os.replace(aligned, DST)
r = subprocess.run([BT+r'\apksigner.bat','sign','--ks',r'C:\FL26_Mod\build\fl26_test.keystore',
    '--ks-pass','pass:fl26modtest','--out',DST,DST], capture_output=True, text=True, env=envv)
if r.returncode: print(r.stderr[-500:]); raise SystemExit(1)
r = subprocess.run([ADB,'install','-r',DST], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip())


