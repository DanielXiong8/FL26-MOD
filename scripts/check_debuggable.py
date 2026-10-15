# -*- coding: utf-8 -*-
"""Check if the installed APK is really debuggable; if not, fix manifest and rebuild."""
import sys, io, zipfile, shutil, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

APK = r'C:\FL26_Mod\dist\fl26_mod_4a_v8.apk'

# Use apkanalyzer / aapt to check manifest debuggable flag
AAPT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0\aapt2.exe'
if not os.path.exists(AAPT):
    AAPT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0\aapt.exe'
print("aapt exists:", os.path.exists(AAPT))

env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')

r = subprocess.run([AAPT, 'dump', 'badging', APK], capture_output=True, text=True, env=env_vars)
out = r.stdout + r.stderr
for line in out.splitlines()[:15]:
    print(line)

# check debuggable via xmltree
r2 = subprocess.run([AAPT, 'dump', 'xmltree', APK, 'AndroidManifest.xml'], capture_output=True, text=True, env=env_vars)
txt = r2.stdout
for line in txt.splitlines():
    if 'debuggable' in line.lower() or 'application' in line.lower()[:60]:
        print(line)
