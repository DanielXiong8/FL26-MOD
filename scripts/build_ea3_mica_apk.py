# -*- coding: utf-8 -*-
# build_eastasia_apk.py - avatar(baked EA face) + gamedata(Ralla b1=22, b7=127) -> APK -> install
import struct, io, os, shutil, zipfile, subprocess
import numpy as np
from PIL import Image
import UnityPy

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')

# ---------- 1. avatar: inject baked EA face ----------
TARGET = "assets/models/player2021/textures/face/face_eastasia_new1.png"
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
tex = env.container[TARGET].read()
img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea3.png').convert('RGB')
tex.set_image(img); tex.save()
AV = r'C:\FL26_Mod\build\avatar_ea3_mica.unity3d'
open(AV,'wb').write(env.file.save(packer='original'))
env2 = UnityPy.load(AV)
d = np.abs(np.array(env2.container[TARGET].read().image.convert('RGB'),np.float32)-np.array(img,np.float32)).mean()
print('avatar inject diff %.2f' % d)

# ---------- 2. gamedata: patch Ralla 103346 appearance in place ----------
GD = r'C:\FL26_Mod\build\gamedata.unity3d'
GD_OUT = r'C:\FL26_Mod\modified\gamedata_ea3.unity3d'
os.makedirs(os.path.dirname(GD_OUT), exist_ok=True)
gen = UnityPy.load(GD)
pa_raw = None
for obj in gen.objects:
    if obj.type.name == 'TextAsset':
        dd = obj.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            raw = dd.m_Script
            pa_raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw,str) else bytes(raw)
assert pa_raw, 'PlayerAppearanceTable not found'
n = struct.unpack_from("<I", pa_raw, 0)[0]
PID = 103346
off = None
for i in range(n):
    k, o = struct.unpack_from("<II", pa_raw, 4 + i*8)
    if k == PID: off = o; break
assert off is not None, 'Ralla pid not in appearance table'
rec = bytearray(pa_raw[off:off+21])
assert struct.unpack_from("<I", rec, 0)[0] == PID
print('Ralla app before:', rec[4:].hex())
rec[4+1] = 22    # b1: face_eastasia_new1
rec[4+7] = 127   # b7: no beard
new_pa = pa_raw[:off] + bytes(rec) + pa_raw[off+21:]
print('Ralla app after :', rec[4:].hex())

shutil.copy2(GD, GD_OUT)
g2 = UnityPy.load(GD_OUT)
for obj in g2.objects:
    if obj.type.name == 'TextAsset':
        dd = obj.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            dd.m_Script = new_pa.decode('utf-8', errors='surrogateescape')
            dd.save()
with open(GD_OUT,'wb') as f:
    f.write(g2.file.save())
# verify roundtrip
g3 = UnityPy.load(GD_OUT)
for obj in g3.objects:
    if obj.type.name == 'TextAsset':
        dd = obj.read(check_read=False)
        if dd.m_Name == 'PlayerAppearanceTable':
            r2 = dd.m_Script
            r2 = r2.encode('utf-8', errors='surrogateescape') if isinstance(r2,str) else bytes(r2)
for i in range(struct.unpack_from("<I", r2, 0)[0]):
    k, o = struct.unpack_from("<II", r2, 4 + i*8)
    if k == PID:
        print('roundtrip rec:', r2[o:o+21].hex())
        break

# ---------- 3. APK ----------
DST = r'C:\FL26_Mod\dist\fl26_ea3_mica.apk'
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


