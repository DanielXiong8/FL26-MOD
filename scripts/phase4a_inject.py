# -*- coding: utf-8 -*-
"""
Phase 4A: Inject modified gamedata.unity3d into APK, sign, install.
"""
import zipfile, shutil, os, subprocess, sys

SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
MOD_BUNDLE = r'C:\FL26_Mod\modified\gamedata_new_player.unity3d'
DST_APK = r'C:\FL26_Mod\dist\fl26_mod_4a_test.apk'
BUNDLE_PATH_IN_APK = 'assets/bundles/gamedata.unity3d'

# Tools
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
KEYSTORE = r'C:\FL26_Mod\build\fl26_test.keystore'
KS_PASS = 'fl26modtest'

print("=" * 60)
print("Phase 4A: APK Injection")
print("=" * 60)

# Step 1: Replace bundle in APK
print("\n[1/5] Replacing gamedata.unity3d in APK...")
os.makedirs(os.path.dirname(DST_APK), exist_ok=True)

# Read original APK, replace bundle, write new APK
with zipfile.ZipFile(SRC_APK, 'r') as zin:
    with zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == BUNDLE_PATH_IN_APK:
                # Replace with modified bundle
                with open(MOD_BUNDLE, 'rb') as f:
                    zout.writestr(item, f.read())
                print(f"  Replaced: {BUNDLE_PATH_IN_APK} ({os.path.getsize(MOD_BUNDLE):,} bytes)")
            else:
                zout.writestr(item, zin.read(item.filename))

shutil.move(DST_APK + '.tmp', DST_APK)
print(f"  Output: {DST_APK} ({os.path.getsize(DST_APK):,} bytes)")

# Step 2: Zipalign
print("\n[2/5] Zipalign...")
aligned = DST_APK.replace('.apk', '_aligned.apk')
result = subprocess.run([ZIPALIGN, '-p', '-f', '4', DST_APK, aligned],
                       capture_output=True, text=True)
if result.returncode != 0:
    print(f"  ERROR: {result.stderr}")
    sys.exit(1)
os.replace(aligned, DST_APK)
print(f"  Aligned: {DST_APK}")

# Step 3: Sign
print("\n[3/5] Signing...")
result = subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE,
                        '--ks-pass', f'pass:{KS_PASS}',
                        '--ks-key-alias', 'fl26test',
                        DST_APK],
                       capture_output=True, text=True)
if result.returncode != 0:
    print(f"  ERROR: {result.stderr}")
    sys.exit(1)
print(f"  Signed: {DST_APK}")

# Step 4: Verify
print("\n[4/5] Verifying...")
result = subprocess.run([APKSIGNER, 'verify', '--print-certs', DST_APK],
                       capture_output=True, text=True)
if result.returncode != 0:
    print(f"  ERROR: {result.stderr}")
    sys.exit(1)
print(f"  Signature verified")

# Step 5: Install
print("\n[5/5] Installing...")
result = subprocess.run([ADB, 'install', '-r', DST_APK],
                       capture_output=True, text=True, timeout=120)
print(f"  {result.stdout.strip()}")
if result.returncode != 0:
    print(f"  ERROR: {result.stderr}")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"INSTALL COMPLETE")
print(f"{'='*60}")
print(f"APK: {DST_APK}")
print(f"Size: {os.path.getsize(DST_APK):,} bytes")
print(f"\nTest instructions:")
print(f"1. Open FL26 Mod on device")
print(f"2. Go to League mode")
print(f"3. Select team 20026 (small team)")
print(f"4. Look for player 'CustomLeagueTest' (pid=180001)")
print(f"5. Check if player appears in roster")
print(f"6. Try to start a match")
