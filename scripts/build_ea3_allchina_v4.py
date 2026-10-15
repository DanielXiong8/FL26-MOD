# -*- coding: utf-8 -*-
"""build_ea3_allchina_v4.py
- new1: MICA verts + ea3 (unchanged pipeline)
- new5/6: geometry & UV untouched; texture = ea3 (UV layout identical to new1)
- new2/3/4: geometry & UV untouched; texture T_m baked: T_m[uv_m] = ea3[uv_new1[NN3d(i)]]
  (barycentric via scipy.griddata linear + nearest outside hull)
- Ralla b1=22 b7=127
"""
import struct, os, shutil, zipfile, subprocess, json
import numpy as np
from PIL import Image
import UnityPy
from scipy.spatial import cKDTree
from scipy.interpolate import griddata

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
    uv_raw = np.frombuffer(data[s0len:], np.float32)
    uv0 = uv_raw.reshape(-1, 2)[:n].astype(np.float64)
    return pos, uv0

ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'))
V1 = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
meshes = {}
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name.startswith('face_EastAsia_new'):
            meshes[m.m_Name] = (o, m)

o1, m1 = meshes['face_EastAsia_new1']
t1 = o1.read_typetree()
pos1, uv1 = parse_mesh(t1['m_VertexData'])
kd = cKDTree(pos1)
ea3 = np.array(Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea3.png').convert('RGB'), np.uint8)
H, W = ea3.shape[:2]

def sample_ea3(uv):
    x = np.clip((uv[:, 0] % 1.0) * W, 0, W-1).astype(int)
    y = np.clip((1.0 - (uv[:, 1] % 1.0)) * H, 0, H-1).astype(int)
    return ea3[y, x]

for name in sorted(meshes):
    fam = int(name[-1])
    o, m = meshes[name]
    tree = o.read_typetree()
    vd = tree['m_VertexData']
    n = vd['m_VertexCount']
    if name == 'face_EastAsia_new1':
        data = bytearray(bytes(vd['m_DataSize']))
        stride = 40
        for i in range(n):
            off = i * stride
            data[off:off+12] = V1[i].astype('<f4').tobytes()
        vd['m_DataSize'] = bytes(data)
        tree['m_VertexData'] = vd
        o.save_typetree(tree)
        tex_img = Image.fromarray(ea3)
    elif fam in (5, 6):
        # geometry/UV untouched; texture = ea3 directly
        tex_img = Image.fromarray(ea3)
    else:
        pos_m, uv_m = parse_mesh(vd)
        _, idx = kd.query(pos_m)
        print('%s 3D-NN mean=%.5f max=%.5f' % (name, _ .mean(), _.max()))
        src_uv = uv1[idx]                 # corresponding point in new1 atlas
        colors = sample_ea3(src_uv)       # Ma Jiantao color per vertex
        # bake into mesh's own atlas layout
        gx, gy = np.meshgrid(np.arange(W), np.arange(H))
        pts = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float64)
        uv_pix = np.stack([uv_m[:, 0] * W, (1.0 - uv_m[:, 1]) * H], 1)
        remap = griddata(uv_pix, colors.astype(np.float64), pts, method='linear')
        hole = np.isnan(remap[:, 0])
        if hole.any():
            remap_near = griddata(uv_pix, colors.astype(np.float64), pts[hole], method='nearest')
            remap[hole] = remap_near
        tex_img = Image.fromarray(remap.reshape(H, W, 3).astype(np.uint8))
        out = r'C:\FL26_Mod\work\face_pipeline\track_d\ea3_remap_new%d.png' % fam
        tex_img.save(out)
    tex = env.container['assets/models/player2021/textures/face/face_eastasia_new%d.png' % fam].read()
    tex.set_image(tex_img); tex.save()
    print(name, 'texture baked')

AV = r'C:\FL26_Mod\build\avatar_ea3_v4.unity3d'
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
        if m.m_Name in ('face_EastAsia_new5', 'face_EastAsia_new6', 'face_EastAsia_new4'):
            print(m.m_Name, 'untouched vc=', m.m_VertexData.m_VertexCount)

# gamedata
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_v4.unity3d'
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

DST = r'C:\FL26_Mod\dist\fl26_allchina_v4.apk'
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

