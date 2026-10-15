# -*- coding: utf-8 -*-
"""Step 11 E2E avatar injection: put the NEW photo's face model into the E2E APK.

1. Extract assets/bundles/avatar.unity3d from dist/fl26_e2e.apk
2. face_EastAsia_new1 mesh  <- stage2_ea1.json adapted verts (MICA fit from the new photo)
3. face_eastAsia_new1 texture <- work/face_pipeline/track_d/baked_mjt_v1.png (fresh bake)
4. Repack into the APK, zipalign + sign
"""
import struct, sys, io, os, shutil, zipfile, subprocess, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
from PIL import Image
import UnityPy

ROOT = r'D:\FL26_Mod'
E2E_APK = os.path.join(ROOT, 'dist', 'fl26_e2e.apk')
AV_EXTRACT = os.path.join(ROOT, 'build', 'e2e_avatar_src.unity3d')
AV_DST = os.path.join(ROOT, 'modified', 'avatar_e2e.unity3d')
EA1 = os.path.join(ROOT, 'work', 'face_pipeline', 'uv', 'mesh_ea1.json')
ADAPT = os.path.join(ROOT, 'face_benchmark', 'adapter', 'stage2_ea1.json')
BAKE = os.path.join(ROOT, 'work', 'face_pipeline', 'track_d', 'baked_mjt_v1.png')
MESH_NAME = 'face_EastAsia_new1'
TEX_NAME = 'face_eastAsia_new1'

BT = os.path.join(ROOT, 'android-sdk', 'build-tools', '36.0.0')
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
KEYSTORE = os.path.join(ROOT, 'build', 'fl26_test.keystore')

# ---------- extract avatar bundle ----------
if not os.path.exists(AV_EXTRACT) or os.environ.get('FORCE_EXTRACT'):
    with zipfile.ZipFile(E2E_APK) as z:
        z.extract('assets/bundles/avatar.unity3d', os.path.dirname(AV_EXTRACT))
    src_av = os.path.join(os.path.dirname(AV_EXTRACT), 'assets/bundles/avatar.unity3d')
    shutil.move(src_av, AV_EXTRACT)
print(f"[base] avatar extracted from {os.path.basename(E2E_APK)}")

shutil.copyfile(AV_EXTRACT, AV_DST)
env = UnityPy.load(AV_DST)

# ---------- 1. mesh: inject the adapted verts ----------
ea1 = np.array(json.load(open(EA1))['vertices'], np.float64)
adapt = np.array(json.load(open(ADAPT))['vertices'], np.float64)
assert adapt.shape == ea1.shape == (700, 3), (adapt.shape, ea1.shape)

mesh_done = False
for obj in env.objects:
    if obj.type.name == 'Mesh':
        m = obj.read()
        if m.m_Name != MESH_NAME:
            continue
        tree = obj.read_typetree()
        vd = tree['m_VertexData']
        nvert = vd['m_VertexCount']
        ch0 = vd['m_Channels'][0]
        stride = 0
        for ch in vd['m_Channels']:
            if ch['stream'] == 0:
                stride = max(stride, ch['offset'] + ch['dimension'] * 4)
        data = bytearray(bytes(vd['m_DataSize']))
        fl = np.frombuffer(bytes(data), np.float32)
        pos_all = fl.reshape(-1, stride // 4)[:, ch0['offset']//4:ch0['offset']//4+3]
        # parse-convention check: game x = -mesh_ea1 x (verified in the v5c pipeline)
        d_chk = np.abs(pos_all[:nvert] * np.array([-1.0, 1.0, 1.0]) - ea1.astype(np.float32)).max()
        print(f'[{MESH_NAME}] vc={nvert} parse-vs-original-ea1 (x-flip) max diff = {d_chk:.4f} (>1.0 expected: MICA verts already injected)')
        adapt_g = adapt * np.array([-1.0, 1.0, 1.0])
        for i in range(nvert):
            o = i * stride
            data[o:o+12] = adapt_g[i].astype('<f4').tobytes()
        vd['m_DataSize'] = bytes(data)
        tree['m_VertexData'] = vd
        obj.save_typetree(tree)
        mesh_done = True
        break
assert mesh_done, 'face_EastAsia_new1 mesh not found'
print('[mesh] MICA verts injected (new photo)')

# ---------- 2. texture: the fresh bake ----------
bake_img = Image.open(BAKE).convert('RGB')
tex_done = False
for obj in env.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read()
        if d.m_Name == TEX_NAME:
            d.set_image(bake_img)
            d.save()
            tex_done = True
            break
assert tex_done, 'face_eastAsia_new1 texture not found'
print(f'[texture] {TEX_NAME} <- fresh bake {bake_img.size}')

# ---------- 3. save the bundle ----------
with open(AV_DST, 'wb') as f:
    f.write(env.file.save())
print(f'[bundle] saved: {AV_DST} {os.path.getsize(AV_DST)} bytes')

# ---------- 4. repack the APK ----------
with zipfile.ZipFile(E2E_APK, 'r') as zin:
    with zipfile.ZipFile(E2E_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/avatar.unity3d':
                with open(AV_DST, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(E2E_APK + '.tmp', E2E_APK)

env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')
aligned = E2E_APK.replace('.apk', '_aligned.apk')
subprocess.run([ZIPALIGN, '-p', '-f', '4', E2E_APK, aligned], capture_output=True, env=env_vars)
if os.path.exists(aligned): os.replace(aligned, E2E_APK)
r = subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE, '--ks-pass', 'pass:fl26modtest',
                    '--ks-key-alias', 'fl26test', E2E_APK], capture_output=True, text=True, env=env_vars)
print("sign:", 'OK' if r.returncode == 0 else r.stderr[-300:])
v = subprocess.run([APKSIGNER, 'verify', E2E_APK], capture_output=True, text=True, env=env_vars)
print("verify:", 'OK' if v.returncode == 0 else v.stdout[-200:])
print(f"\nDONE: {E2E_APK}")
