# -*- coding: utf-8 -*-
"""build_ea3_allchina_v3.py
Fix vs v2: per-mesh UV shell alignment via 2D similarity RANSAC (instead of raw NN uv copy),
which fixes A-type hard fragments and B-type mottling.
  - new1: MICA verts, all 6 textures = baked_ea3
  - new2..6: keep shape; uv0 := S(uv0_original) where S maps mesh's shell onto new1 atlas
  - Ralla b1=22 b7=127
"""
import struct, os, shutil, zipfile, subprocess, json
import numpy as np
from PIL import Image
import UnityPy

rng = np.random.default_rng(7)

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

def parse_mesh(vd):
    n = vd['m_VertexCount']
    data = bytes(vd['m_DataSize'])
    stride = 0
    for ch in vd['m_Channels']:
        if ch['stream'] == 0: stride = max(stride, ch['offset'] + ch['dimension'] * 4)
    fl = np.frombuffer(data, np.float32)
    pos = fl[:n*stride//4].reshape(n, stride//4)[:, 0:3].astype(np.float64).copy()
    s0len = n * stride
    uv_raw = np.frombuffer(data[s0len:], np.float32).copy()
    uv0 = uv_raw.reshape(-1, 2)[:n].astype(np.float64)
    return pos, uv0, bytearray(data), stride, s0len

def sim_tform(src, dst):
    """least-squares similarity src->dst (2D). src,dst (N,2)"""
    sc, dc = src.mean(0), dst.mean(0)
    a, b = src - sc, dst - dc
    cov = (a.T @ b) / len(a)
    U, S, Vt = np.linalg.svd(cov)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, d]) @ U.T
    s = (S * [1, d]).sum() / (a**2).sum()
    t = dc - s * R @ sc
    return s, R, t

def apply_tform(S, pts):
    s, R, t = S
    return (s * (pts @ R.T)) + t

def ransac_sim(src, dst, iters=4000, tol=0.004):
    best = None
    n = len(src)
    for _ in range(iters):
        i = rng.choice(n, 2, replace=False)
        try:
            S = sim_tform(src[i], dst[i])
        except Exception:
            continue
        res = np.abs(apply_tform(S, src) - dst).max(1)
        inl = res < tol
        if best is None or inl.sum() > best[0]:
            best = (inl.sum(), inl)
    inl = best[1]
    S = sim_tform(src[inl], dst[inl])
    res = np.abs(apply_tform(S, src) - dst).max(1)
    inl = res < tol
    S = sim_tform(src[inl], dst[inl])
    return S, inl.mean(), res[inl].mean()

ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'))
V1 = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
meshes = {}
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name.startswith('face_EastAsia_new'):
            meshes[m.m_Name] = (o, m)

img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea3.png').convert('RGB')
for name in sorted(meshes):
    fam = int(name[-1])
    tex = env.container['assets/models/player2021/textures/face/face_eastasia_new%d.png' % fam].read()
    tex.set_image(img); tex.save()

o1, m1 = meshes['face_EastAsia_new1']
tree1 = o1.read_typetree()
_, uv1_0, data1, stride1, s0len1 = parse_mesh(tree1['m_VertexData'])

for name in sorted(meshes):
    o, m = meshes[name]
    tree = o.read_typetree()
    vd = tree['m_VertexData']
    pos, uv0, data, stride, s0len = parse_mesh(vd)
    n = vd['m_VertexCount']
    if name == 'face_EastAsia_new1':
        for i in range(n):
            off = i * stride
            data[off:off+12] = V1[i].astype('<f4').tobytes()
    else:
        S, frac, res = ransac_sim(uv0, uv1_0[:len(uv0)])
        print('%s inlier=%.2f%% med_res=%.5f' % (name, frac*100, res))
        uv_new = apply_tform(S, uv0)
        uv_raw = np.frombuffer(bytes(data[s0len:]), np.float32).copy()
        uv_arr = uv_raw.reshape(-1, 2)
        uv_arr[:n] = uv_new.astype(np.float32)
        data = data[:s0len] + bytearray(uv_arr.tobytes())
    vd['m_DataSize'] = bytes(data)
    tree['m_VertexData'] = vd
    o.save_typetree(tree)

AV = r'C:\FL26_Mod\build\avatar_ea3_allchina_v3.unity3d'
with open(AV, 'wb') as f:
    f.write(env.file.save(packer='original'))

env2 = UnityPy.load(AV)
for o in env2.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name == 'face_EastAsia_new1':
            fl = np.frombuffer(bytes(m.m_VertexData.m_DataSize), np.float32).reshape(-1, 10)[:700]
            assert np.abs(fl[:, :3] - V1.astype(np.float32)).max() < 1e-5
            print('new1 MICA verified')
        if m.m_Name == 'face_EastAsia_new3':
            print('new3 reloaded vc=', m.m_VertexData.m_VertexCount)

GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_v3.unity3d'
gen = UnityPy.load(GD)
pa_raw = None
for o in gen.objects:
    if o.type.name == 'TextAsset':
        d = o.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            raw = d.m_Script
            pa_raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
n = struct.unpack_from('<I', pa_raw, 0)[0]
for i in range(n):
    k, o = struct.unpack_from('<II', pa_raw, 4 + i*8)
    if k == 103346:
        off = o; break
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

DST = r'C:\FL26_Mod\dist\fl26_allchina_v3.apk'
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
