# -*- coding: utf-8 -*-
"""regression_driver.py — full-pipeline regression for one photo set.
Usage: python regression_driver.py <set_name> <primary_photo> <out_dir>
Outputs (per set): preprocess, golden bake, photo skeleton, MICA renders,
game-equivalent renders (front/45L/45R/side) = what the APK displays.
"""
import os, sys, shutil, subprocess, json

ROOT = r'D:\FL26_Mod'
PH14 = os.path.join(ROOT, 'work', 'face_pipeline', 'phase14a5')
RECON = os.path.join(ROOT, 'face_benchmark', 'envs', 'envs', 'recon', 'python.exe')
BAKE8 = os.path.join(PH14, '..', 'track_user1', 'bake8_user.py')
GMP = os.path.join(PH14, 'geowarp_mp.py')
PREP = os.path.join(PH14, 'preprocess.py')
MREND = os.path.join(PH14, 'mica_render.py')

set_name, photo, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
work = os.path.join(out, 'work')
os.makedirs(work, exist_ok=True)
log = lambda m: print('[driver:%s] %s' % (set_name, m), flush=True)

# 1) preprocess (recon env: cv2)
log('preprocess')
r = subprocess.run([RECON, PREP, photo, os.path.join(work, 'tight.jpg')],
                   capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-500:]); raise SystemExit('preprocess failed')
tight = os.path.join(work, 'tight.jpg')

# 2) golden bake8 (recon env: mediapipe+cv2)
log('golden bake8')
r = subprocess.run([RECON, BAKE8, tight], cwd=os.path.dirname(BAKE8),
                   capture_output=True, text=True)
bake_src = os.path.join(os.path.dirname(BAKE8), 'baked_ea3.png')
if r.returncode != 0 or not os.path.exists(bake_src):
    print(r.stderr[-500:]); raise SystemExit('bake8 failed')
shutil.copyfile(bake_src, os.path.join(out, 'bake_face_texture.png'))
log('bake ok')

# 3) photo skeleton (recon env: mediapipe)
log('photo skeleton (MediaPipe)')
stage2 = os.path.join(out, 'skeleton_stage2.json')
r = subprocess.run([RECON, GMP, tight, stage2], capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-500:]); raise SystemExit('geowarp_mp failed')
log('skeleton ok')

# 4) MICA chain (system python driver; MICA step spawns recon internally)
log('MICA chain (~2 min)')
chain_out = os.path.join(out, 'mica_mesh')
r = subprocess.run([sys.executable, os.path.join(PH14, 'chain_geometry.py'),
                    '--photo', tight, '--run', chain_out],
                   capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-500:]); raise SystemExit('MICA chain failed')
log('MICA ok')

# 5) MICA renders (recon env: trimesh+matplotlib)
log('MICA renders')
r = subprocess.run([RECON, MREND, os.path.join(chain_out, 'mica', 'mesh.obj'),
                    os.path.join(out, 'mica_views'), set_name + ' MICA'],
                   capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-500:]); raise SystemExit('mica render failed')
log('mica renders ok')

# 6) game-equivalent renders = what the APK displays (system python + Unity)
log('game renders (Unity ~40s)')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'FL26_FaceBuilderWeb', 'backend'))
import preview
views = preview.render(bake_src, stage2_json=stage2)
import urllib.request
for tag, url in views.items():
    p = url.replace('/api/file/', '')
    dst = os.path.join(out, 'game_%s.png' % tag)
    shutil.copyfile(p, dst)
    log('game_%s.png saved' % tag)

print('[driver:%s] DONE -> %s' % (set_name, out), flush=True)
