# -*- coding: utf-8 -*-
# build_face_v4.py - device build for the skeleton-anchored bake (compare_v4 chain).
# Flow: inject player (zero-clone, slot auto) -> texture_inject (baked_wide relit)
#       -> zipalign+sign -> registry.add -> adb install -r
import os, sys, json, hashlib, shutil, subprocess as sp

ROOT = r'D:\FL26_Mod'
BACKEND = os.path.join(ROOT, 'tools', 'FL26_FaceBuilderWeb', 'backend')
BT = os.path.join(ROOT, 'android-sdk', 'build-tools', '36.0.0')
ADB = os.path.join(ROOT, 'android-sdk', 'platform-tools', 'adb.exe')
BASE_APK = os.path.join(ROOT, 'build', 'base_debuggable2.apk')
KS = os.path.join(ROOT, 'build', 'fl26_test.keystore')
WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
RUN_DIR = os.path.join(WORK, 'build_v4')
BAKE = os.path.join(WORK, 'baked_full.png')
STAGE2 = os.path.join(WORK, 'stage2_sculpt.json')
NAME = 'MyFaceV5'

sys.path.insert(0, BACKEND)
os.makedirs(RUN_DIR, exist_ok=True)

import registry as reg
import appearance_state as AS

team_id = 10027   # 10059 roster full (33/33); placeholder squad has space
used = reg.jerseys_in_team(team_id)
base_jerseys = {30, 40, 99}  # known device-used; injector re-validates vs gamedata
jersey = next(j for j in range(60, 99) if j not in used and j not in base_jerseys)
print('[v4] free jersey in team %d: %d (used: %s)' % (team_id, jersey, sorted(used)))

cfg = AS.build_state({
    'reference_pid': 0, 'name': NAME, 'position': 'FW',
    'nat': 24, 'team_id': team_id, 'jersey': jersey,
    'skin_tone': 6, 'face_texture_id': 10,     # b1=10 -> new1: the ONLY slot whose mesh matches our 700-vert topology
    'hair_color_id': 2, 'eyebrow_index': 1,
    'beard_enabled': False, 'beard_style_id': 1,   # mustache already in the bake
    'b14': 18,
})
print('[v4] player inject...')
res = inject = __import__('inject_player_v1').run(cfg, RUN_DIR)
pid, apk = res['pid'], res['apk']
slot = int(cfg['explicit']['face_texture_id'])
print('[v4] PASS pid=%d jersey=%d slot=b1=%d (new%d)' % (pid, res['jersey'], slot, slot - 9))

print('[v4] mesh+texture inject (mannequin + collapsed lids + decal)...')
import mesh_inject
apk, _ = mesh_inject.run(apk, STAGE2, BAKE, RUN_DIR, slot_b1=slot)

print('[v4] zipalign + sign...')
JH = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
envv = dict(os.environ)
envv['JAVA_HOME'] = JH
envv['Path'] = JH + r'\bin;' + envv.get('Path', '')
aligned = apk.replace('.apk', '_al.apk')
r = sp.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', apk, aligned],
           capture_output=True, env=envv)
if os.path.exists(aligned):
    os.replace(aligned, apk)
r = sp.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', KS,
            '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', apk],
           capture_output=True, text=True, env=envv)
assert r.returncode == 0, 'sign failed: ' + (r.stderr or '')[-300:]

h = hashlib.sha256()
with open(apk, 'rb') as f:
    for c in iter(lambda: f.read(1 << 20), b''):
        h.update(c)
sha = h.hexdigest()

reg.add(pid, NAME, team_id, res['jersey'], sha,
        slot_note='mannequin+decal+lid-collapse v6 (b1=%d new%d)' % (slot, slot - 9),
        nat=24, face_texture_id=slot, b14=18)
print('[v4] registered pid=%d sha=%s...' % (pid, sha[:12]))

print('[v4] APK: %s (%d bytes)' % (apk, os.path.getsize(apk)))
r = sp.run([ADB, 'devices'], capture_output=True, text=True)
lines = [l for l in r.stdout.strip().split('\n')[1:] if l.strip()]
if lines and 'device' in lines[0]:
    print('[v4] device online, installing...')
    r = sp.run([ADB, 'install', '-r', apk], capture_output=True, text=True)
    print('[v4] install:', (r.stdout or r.stderr).strip())
else:
    print('[v4] NO DEVICE - install manually: %s' % apk)
