# -*- coding: utf-8 -*-
"""build_ea3_allchina_v5.py
v4 + upgrades:
  1. new2/3/4 remap: per-triangle affine rasterization (real index buffer, per-pixel ea3 sampling)
  2. eyeball submesh (first submesh, 32 tris) vertices shrunk 15% toward centroid -> fixes protruding eyes
  - new1: MICA verts + ea3; new5/6: untouched + ea3; Ralla b1=22 b7=127
"""
import struct, os, shutil, zipfile, subprocess, json
# -*- coding: utf-8 -*-
"""AUTO-GENERATED from build_ea3_allchina_v5.py (v5 frozen, do not edit v5).
Usage: python build_ea3_candidate_apk.py <candidate_baked.png> <apk_name.apk>
Outputs all intermediates under runs/test01/apk_<cand>/"""
import sys as _sys
CAND_BAKED = _sys.argv[1] if len(_sys.argv) > 1 else r'C:\FL26_Mod\face_benchmark\runs\test01\candidates\c4\baked.png'
APK_NAME = _sys.argv[2] if len(_sys.argv) > 2 else 'fl26_candidate_c4.apk'
APK_DIR = os.path.join(r'C:\FL26_Mod\face_benchmark\runs\test01', 'apk_' + os.path.splitext(os.path.basename(CAND_BAKED))[0])
os.makedirs(APK_DIR, exist_ok=True)
print('candidate:', CAND_BAKED); print('workdir:', APK_DIR)

import numpy as np
from PIL import Image
import UnityPy
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt, map_coordinates

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

EYE_SHRINK = 0.85

def mesh_data(tree):
    vd = tree['m_VertexData']
    n = vd['m_VertexCount']
    data = bytes(vd['m_DataSize'])
    stride = 0
    for ch in vd['m_Channels']:
        if ch['stream'] == 0: stride = max(stride, ch['offset'] + ch['dimension'] * 4)
    fl = np.frombuffer(data, np.float32)
    pos = fl[:n*stride//4].reshape(n, stride//4)[:, 0:3].astype(np.float64).copy()
    s0len = n * stride
    uv_raw = np.frombuffer(data[s0len:], np.float32)
    uv0 = uv_raw.reshape(-1, 2)[:n].astype(np.float64)
    idx = np.frombuffer(bytes(tree['m_IndexBuffer']), np.uint16).astype(np.int64)
    subs = [(s['firstByte']//2, s['indexCount']) for s in tree['m_SubMeshes']]
    return n, pos, uv0, bytearray(data), stride, s0len, idx, subs

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
meshes = {}
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name.startswith('face_EastAsia_new'):
            meshes[m.m_Name] = (o, m)

# ---- new1 reference ----
o1, m1 = meshes['face_EastAsia_new1']
t1 = o1.read_typetree()
n1, pos1, uv1, data1, stride1, s0len1, idx1, subs1 = mesh_data(t1)
kd = cKDTree(pos1)
ea3 = np.array(Image.open(CAND_BAKED).convert('RGB'), np.uint8)
ea3_f32 = ea3.astype(np.float32)
ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'))
V1 = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])
H, W = ea3.shape[:2]

def uv_to_px(uv):
    return np.stack([np.clip(uv[:, 0] % 1.0, 0, 1) * (W-1), np.clip(1.0 - (uv[:, 1] % 1.0), 0, 1) * (H-1)], 1)

# nearest-fill ea3 outside valid zone to reduce garbage at grazing samples (edt)
valid = ~((ea3.astype(int).sum(2) < 30))  # near-black = invalid
if valid.all():
    filled = ea3
else:
    ind = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    filled = ea3[ind[0], ind[1]]
ea3f = Image.fromarray(filled)

for name in sorted(meshes):
    fam = int(name[-1])
    o, m = meshes[name]
    tree = o.read_typetree()
    n, pos, uv0, data, stride, s0len, idx, subs = mesh_data(tree)
    if name == 'face_EastAsia_new1':
        for i in range(n):
            off = i * stride
            data[off:off+12] = V1[i].astype('<f4').tobytes()
        vd = tree['m_VertexData']; vd['m_DataSize'] = bytes(data); tree['m_VertexData'] = vd
        o.save_typetree(tree)
        tex_img = ea3f
    else:
        # eyeball shrink (submesh 0) for all non-new1 meshes
        e0, ec = subs[0]
        eidx = idx[e0:e0+ec]
        everts = np.unique(eidx)
        cen = pos[everts].mean(0)
        data = bytearray(data)
        for i in everts:
            p = pos[i] * EYE_SHRINK + cen * (1 - EYE_SHRINK)
            data[i*stride:i*stride+12] = p.astype('<f4').tobytes()
        vd = tree['m_VertexData']; vd['m_DataSize'] = bytes(data); tree['m_VertexData'] = vd
        o.save_typetree(tree)
        if fam in (5, 6):
            tex_img = ea3f
        else:
            # per-triangle affine remap of ea3 into this mesh's atlas
            _, nn = kd.query(pos)
            src_px = uv_to_px(uv1[nn])   # in ea3
            dst_px = np.stack([uv0[:, 0] * W, (1.0 - uv0[:, 1]) * H], 1)  # in target
            # face triangles = largest submesh
            big = max(subs, key=lambda s: s[1])
            f0, fc = big
            tris = idx[f0:f0+fc].reshape(-1, 3)
            Tm = np.array(ea3f, np.uint8).copy()
            for t in tris:
                sxy = src_px[t]; dxy = dst_px[t]
                # solve INVERSE affine (dst->src) directly
                A = np.zeros((6, 6)); rhs = np.zeros(6)
                for k3 in range(3):
                    A[2*k3]   = [dxy[k3,0], dxy[k3,1], 1, 0, 0, 0]
                    A[2*k3+1] = [0, 0, 0, dxy[k3,0], dxy[k3,1], 1]
                    rhs[2*k3] = sxy[k3,0]; rhs[2*k3+1] = sxy[k3,1]
                try:
                    coef = np.linalg.solve(A, rhs)
                except np.linalg.LinAlgError:
                    continue
                x0, y0 = np.floor(dxy.min(0)).astype(int); x1, y1 = np.ceil(dxy.max(0)).astype(int)
                x0,y0 = max(x0,0), max(y0,0); x1,y1 = min(x1,W-1), min(y1,H-1)
                if x1 <= x0 or y1 <= y0: continue
                xs, ys = np.meshgrid(np.arange(x0, x1+1), np.arange(y0, y1+1))
                # point-in-triangle via barycentric
                v0 = dxy[1]-dxy[0]; v1 = dxy[2]-dxy[0]
                v2x = xs - dxy[0,0]; v2y = ys - dxy[0,1]
                den = v0[0]*v1[1]-v1[0]*v0[1]
                if abs(den) < 1e-9: continue
                w1 = (v2x*v1[1]-v1[0]*v2y)/den
                w2 = (v0[0]*v2y-v2x*v0[1])/den
                inside = (w1>=-1e-6)&(w2>=-1e-6)&(w1+w2<=1+1e-6)
                if not inside.any(): continue
                sx = coef[0]*xs + coef[1]*ys + coef[2]
                sy = coef[3]*xs + coef[4]*ys + coef[5]
                # bilinear wrap sampling: kills rounding asymmetry at midline seam
                colors = np.empty((xs.shape[0], xs.shape[1], 3), np.float32)
                for ch3 in range(3):
                    colors[..., ch3] = map_coordinates(ea3_f32[..., ch3], [(sy % H), (sx % W)], order=1, mode='wrap')
                region = Tm[y0:y1+1, x0:x1+1]
                region[inside] = np.clip(colors, 0, 255).astype(np.uint8)[inside]
                Tm[y0:y1+1, x0:x1+1] = region
            tex_img = Image.fromarray(Tm)
            # feather atlas seam columns (u≈0/1): wrap-aware horizontal blend
            arr = np.array(tex_img, np.float32)
            for k in range(1, 5):
                wl = 0.5 ** k
                arr[:, k] = arr[:, k] * (1 - wl) + arr[:, k - 1] * wl
                arr[:, W - 1 - k] = arr[:, W - 1 - k] * (1 - wl) + arr[:, (W - k) % W] * wl
            tex_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
            tex_img.save(os.path.join(APK_DIR, 'remap_new%d.png' % fam))
    tex = env.container['assets/models/player2021/textures/face/face_eastasia_new%d.png' % fam].read()
    tex.set_image(tex_img); tex.save()
    print(name, 'done')

AV = os.path.join(APK_DIR, 'avatar_candidate.unity3d')
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
        if m.m_Name == 'face_EastAsia_new5':
            print('new5 untouched vc=', m.m_VertexData.m_VertexCount)

# gamedata
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = os.path.join(APK_DIR, 'gamedata_candidate.unity3d')
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

DST = os.path.join(r'C:\FL26_Mod\dist', APK_NAME)
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
