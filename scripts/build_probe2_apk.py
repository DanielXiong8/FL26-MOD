# -*- coding: utf-8 -*-
"""build_probe2_apk.py - decisive multi-probe:
  1. ALL eastasia face textures -> magenta (any family member catches)
  2. b1=25 (son_heung_min star face, known token match) for Ralla
  3. probe mesh deform kept on face_EastAsia_new1
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

MAGENTA = Image.new('RGB', (512, 512), (255, 0, 255))

# ---------- 1. avatar: magenta ALL eastasia textures + probe mesh ----------
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
changed = []
for path in list(env.container.keys()):
    if 'eastasia' in path.lower() and path.lower().endswith('.png'):
        tex = env.container[path].read()
        tex.set_image(MAGENTA); tex.save()
        changed.append(path)
print('magenta textures:', changed)
# probe mesh already injected into avatar_probe.unity3d; load that instead for mesh,
# but textures were modified in fresh env -> do both in one file:
obj = None
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name == 'face_EastAsia_new1':
            obj = o; break
assert obj, 'mesh not found'
ad = json.load(open(r'C:\FL26_Mod\face_benchmark\adapter\stage2_probe.json'))
V = np.array(ad['vertices'], np.float64) * np.array([-1.0, 1.0, 1.0])
tree = obj.read_typetree()
vd = tree['m_VertexData']
nvert = vd['m_VertexCount']
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
obj.save_typetree(tree)

AV = r'C:\FL26_Mod\build\avatar_probe2.unity3d'
with open(AV, 'wb') as f:
    f.write(env.file.save(packer='original'))
env2 = UnityPy.load(AV)
n_magenta = 0
for path in env2.container:
    if 'eastasia' in path.lower() and path.lower().endswith('.png'):
        arr = np.array(env2.container[path].read().image.convert('RGB'), np.float32)
        if abs(arr.mean(axis=(0,1))[0] - 255) < 5 and abs(arr.mean(axis=(0,1))[2] - 255) < 5:
            n_magenta += 1
print('magenta verified in output:', n_magenta)

# ---------- 2. gamedata: Ralla b1=25 ----------
import json
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_probe2.unity3d'
gen = UnityPy.load(GD)
pa_raw = None
for o in gen.objects:
    if o.type.name == 'TextAsset':
        dd = o.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            raw = dd.m_Script
            pa_raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
n = struct.unpack_from('<I', pa_raw, 0)[0]
PID = 103346
off = None
for i in range(n):
    k, o = struct.unpack_from('<II', pa_raw, 4 + i*8)
    if k == PID: off = o; break
rec = bytearray(pa_raw[off:off+21])
rec[4+1] = 25   # b1: son_heung_min star face (token match)
rec[4+7] = 127
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

# ---------- 3. APK ----------
import json
DST = r'C:\FL26_Mod\dist\fl26_probe2.apk'
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
