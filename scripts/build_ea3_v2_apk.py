# -*- coding: utf-8 -*-
"""build_ea3_formal_apk.py - formal build:
  avatar: MICA-adapted verts -> ALL 6 face_EastAsia_new1..6 meshes; baked_ea3.png -> face_eastasia_new1.png
  gamedata: Ralla b1=22, b7=127
  -> zipalign + sign + install
"""
import struct, os, shutil, zipfile, subprocess, json
import numpy as np
from PIL import Image
import UnityPy

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

ea1 = np.array(json.load(open(r'C:\FL26_Mod\work\face_pipeline\uv\mesh_ea1.json'))['vertices'], np.float64)
ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'))
V = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])  # game x convention

# ---------- 1. avatar ----------
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea3.png').convert('RGB')
tex = env.container['assets/models/player2021/textures/face/face_eastasia_new1.png'].read()
tex.set_image(img); tex.save()
print('texture baked_ea3 injected')

patched = []
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name == 'face_EastAsia_new1':
            tree = o.read_typetree()
            vd = tree['m_VertexData']
            nvert = vd['m_VertexCount']
            if nvert != 700:
                print('skip %s vc=%d (topology differs)' % (m.m_Name, nvert)); continue
            ch0 = vd['m_Channels'][0]
            data = bytearray(bytes(vd['m_DataSize']))
            stride = 0
            for ch in vd['m_Channels']:
                if ch['stream'] == 0: stride = max(stride, ch['offset'] + ch['dimension'] * 4)
            for i in range(nvert):
                o2 = i * stride + ch0['offset']
                data[o2:o2+12] = V[i].astype('<f4').tobytes()
            vd['m_DataSize'] = bytes(data)
            tree['m_VertexData'] = vd
            o.save_typetree(tree)
            patched.append(m.m_Name)
print('meshes patched:', patched)

AV = r'C:\FL26_Mod\build\avatar_ea3_v2.unity3d'
with open(AV, 'wb') as f:
    f.write(env.file.save(packer='original'))

# verify roundtrip
env2 = UnityPy.load(AV)
cnt = 0
for o in env2.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name in patched:
            fl = np.frombuffer(bytes(m.m_VertexData.m_DataSize), np.float32).reshape(-1, 10)
            P = fl[:700, :3]
            d = np.abs(P - V.astype(np.float32)).max()
            assert d < 1e-5, (m.m_Name, d)
            cnt += 1
print('roundtrip verified meshes:', cnt)

# ---------- 2. gamedata ----------
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_ea3_v2.unity3d'
gen = UnityPy.load(GD)
pa_raw = None
for o in gen.objects:
    if o.type.name == 'TextAsset':
        dd = o.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            raw = dd.m_Script
            pa_raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
n = struct.unpack_from('<I', pa_raw, 0)[0]
off = None
for i in range(n):
    k, o = struct.unpack_from('<II', pa_raw, 4 + i*8)
    if k == 103346: off = o; break
rec = bytearray(pa_raw[off:off+21])
rec[4+1] = 22; rec[4+7] = 127
new_pa = pa_raw[:off] + bytes(rec) + pa_raw[off+21:]
shutil.copy2(GD, GD_OUT)
g2 = UnityPy.load(GD_OUT)
for o in g2.objects:
    if o.type.name == 'TextAsset':
        dd = o.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            dd.m_Script = new_pa.decode('utf-8', errors='surrogateescape')
            dd.save()
with open(GD_OUT, 'wb') as f:
    f.write(g2.file.save())
print('gamedata: Ralla b1=22 b7=127')

# ---------- 3. APK ----------
DST = r'C:\FL26_Mod\dist\fl26_ea3_v2.apk'
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

