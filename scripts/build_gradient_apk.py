# -*- coding: utf-8 -*-
# build_gradient_apk.py - positional-encoding gradient on face texture -> UV probe
import os, zipfile, subprocess
import numpy as np
import UnityPy

TARGET = "assets/models/player2021/textures/face/face_southeuropean_new3.png"
SRC = r'C:\FL26_Mod\build\avatar.unity3d'
AV_OUT = r'C:\FL26_Mod\build\avatar_trackd_grad.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
APK = r'C:\FL26_Mod\build\base_grad.apk'
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'

W = H = 512
xs = np.arange(W)[None,:].repeat(H,0) / (W-1)   # 0 left -> 1 right
ys = np.arange(H)[:,None].repeat(W,1) / (H-1)   # 0 top -> 1 bottom
# R = x, G = y  (B fixed 128). pure function of position.
img = np.stack([(xs*255).astype(np.uint8), (ys*255).astype(np.uint8), np.full((H,W),128,np.uint8)], -1)
from PIL import Image
im = Image.fromarray(img, 'RGB')
im.save(r'C:\FL26_Mod\work\face_pipeline\track_d\uv_probe_gradient.png')

env = UnityPy.load(SRC)
tex = env.container[TARGET].read()
tex.set_image(im)
tex.save()
open(AV_OUT,'wb').write(env.file.save(packer='original'))
env2 = UnityPy.load(AV_OUT)
back = np.array(env2.container[TARGET].read().image.convert('RGB'), np.float32)
print('inject verify diff %.2f' % np.abs(back - img.astype(np.float32)).mean())

with zipfile.ZipFile(SRC_APK) as zin, zipfile.ZipFile(APK,'w') as zout:
    for it in zin.infolist():
        zout.writestr(it, open(AV_OUT,'rb').read() if it.filename=='assets/bundles/avatar.unity3d' else zin.read(it.filename))
envv = dict(os.environ)
envv['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv['Path'] = envv['JAVA_HOME'] + r'\bin;' + envv.get('Path','')
alg = APK.replace('.apk','_aligned.apk')
subprocess.run([BT+r'\zipalign.exe','-p','-f','4',APK,alg], check=True, env=envv)
dist = r'C:\FL26_Mod\dist\fl26_uvprobe.apk'
r = subprocess.run([BT+r'\apksigner.bat','sign','--ks',r'C:\FL26_Mod\build\fl26_test.keystore',
    '--ks-pass','pass:fl26modtest','--key-pass','pass:fl26modtest','--out',dist,alg],
    capture_output=True, text=True, env=envv)
if r.returncode: print(r.stderr[-500:]); raise SystemExit(1)
r = subprocess.run([ADB,'install','-r',dist], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip())
