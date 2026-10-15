# -*- coding: utf-8 -*-
"""build_apk_pl2.py - swap aligned gamedata into base APK, zipalign, sign, install."""
import os, shutil, zipfile, subprocess

ROOT = r'D:\FL26_Mod'
SRC_APK = os.path.join(ROOT, r'build\base_debuggable2.apk')
BUNDLE = os.path.join(ROOT, r'build\gamedata_pl2.unity3d')
DST_APK = os.path.join(ROOT, r'build\fl26_pl_align.apk')
BT = os.path.join(ROOT, r'android-sdk\build-tools\36.0.0')
ADB = os.path.join(ROOT, r'android-sdk\platform-tools\adb.exe')
KEYSTORE = os.path.join(ROOT, r'build\fl26_test.keystore')

with zipfile.ZipFile(SRC_APK, 'r') as zin, \
     zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.filename == 'assets/bundles/gamedata.unity3d':
            with open(BUNDLE, 'rb') as f:
                zout.writestr(item, f.read())
        else:
            zout.writestr(item, zin.read(item.filename))
shutil.move(DST_APK + '.tmp', DST_APK)
print('apk packed: %d bytes' % os.path.getsize(DST_APK))

env = dict(os.environ)
env['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env['Path'] = env['JAVA_HOME'] + r'\bin;' + env.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', DST_APK, aligned],
               capture_output=True, env=env)
os.replace(aligned, DST_APK)
r = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', KEYSTORE,
                    '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', DST_APK],
                   capture_output=True, text=True, env=env)
print('sign:', 'OK' if r.returncode == 0 else r.stderr[-300:])

r = subprocess.run([ADB, 'devices'], capture_output=True, text=True)
print('devices:', r.stdout.strip().replace('\n', ' | '))
r = subprocess.run([ADB, 'install', '-r', DST_APK], capture_output=True, text=True, timeout=300)
print('install:', (r.stdout.strip() or r.stderr.strip())[:200])
