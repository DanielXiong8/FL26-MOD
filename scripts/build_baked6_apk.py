# -*- coding: utf-8 -*-
# build_baked_apk.py - inject baked_ea1.png into avatar.unity3d -> APK -> sign -> install
import os, zipfile, subprocess
import numpy as np
from PIL import Image
import UnityPy

TARGET = "assets/models/player2021/textures/face/face_eastasia_new1.png"
SRC = r'C:\FL26_Mod\build\avatar.unity3d'
AV_OUT = r'C:\FL26_Mod\build\avatar_trackd_baked6.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
APK = r'C:\FL26_Mod\build\base_trackd_baked6.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'

env = UnityPy.load(SRC)
tex = env.container[TARGET].read()
img = Image.open(r'C:\FL26_Mod\work\face_pipeline\track_d\baked_ea1.png').convert('RGB')
tex.set_image(img)
tex.save()
open(AV_OUT,'wb').write(env.file.save(packer='original'))
env2 = UnityPy.load(AV_OUT)
t2 = env2.container[TARGET].read().image
d = np.abs(np.array(t2.convert('RGB'),np.float32) - np.array(img,np.float32)).mean()
print('inject verify diff %.2f' % d)

with zipfile.ZipFile(SRC_APK) as zin, zipfile.ZipFile(APK,'w') as zout:
    for it in zin.infolist():
        zout.writestr(it, open(AV_OUT,'rb').read() if it.filename=='assets/bundles/avatar.unity3d' else zin.read(it.filename))
print('APK rebuilt')

envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')
alg = APK.replace('.apk','_aligned.apk')
subprocess.run([BT+r'\zipalign.exe','-p','-f','4',APK,alg], check=True, env=envv)
dist = r'C:\FL26_Mod\dist\fl26_eastasia_baked.apk'
r = subprocess.run([BT+r'\apksigner.bat','sign','--ks',r'C:\FL26_Mod\build\fl26_test.keystore',
    '--ks-pass','pass:fl26modtest','--key-pass','pass:fl26modtest','--out',dist,alg],
    capture_output=True, text=True, env=envv)
if r.returncode: print(r.stderr[-500:]); raise SystemExit(1)
subprocess.run([BT+r'\apksigner.bat','verify',dist], capture_output=True, env=envv)
print('SIGNED ->', dist)
r = subprocess.run([ADB,'install','-r',dist], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip())
