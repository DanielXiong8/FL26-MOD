# -*- coding: utf-8 -*-
"""
Step 8 Track D: Full pipeline — Photo → Face Texture → Inject → APK Build.

1. Load photo, detect 468 face landmarks via MediaPipe
2. Map 19 FL26 UV landmarks → photo landmarks
3. TPS warp photo → FL26 512×512 RGBA texture
4. Replace face_Ake (idx 47) texture pixels in avatar.unity3d
5. Modify PlayerAppearanceTable: CustomPlayer byte1 30→47
6. Build APK (gamedata + avatar both modified)
7. Install to device
"""
import sys, io, os, json, struct, shutil, math, zipfile, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image
import mediapipe as mp

# ---------- paths ----------
PHOTO = r'C:\Users\Lenovo\OneDrive\Desktop\111.jpg'
IN_DIR = r'C:\FL26_Mod\work\face_pipeline'
OUT_UV = os.path.join(IN_DIR, 'uv')
OUT_GEN = os.path.join(IN_DIR, 'generated')
os.makedirs(OUT_GEN, exist_ok=True)

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'
AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
BUNDLE_DST = r'C:\FL26_Mod\modified\gamedata_custom_face.unity3d'
AVATAR_DST = r'C:\FL26_Mod\modified\avatar_custom_face.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
DST_APK = r'C:\FL26_Mod\dist\fl26_custom_face_test.apk'

TEX_SIZE = 512
CUSTOM_BYTE1 = 47  # face_Ake slot (0 players use it globally)
CUSTOM_PID = 175923

# ---------- 1. load FL26 UV landmarks ----------
with open(os.path.join(OUT_UV, 'uv_landmark_map.json')) as f:
    lm_data = json.load(f)
fl26_uv = {k: v['uv'] for k, v in lm_data['landmarks'].items()}
fl26_names = list(fl26_uv.keys())
fl26_uv_pts = np.array([fl26_uv[n] for n in fl26_names], np.float32)
fl26_tex_pts = np.array([[u * TEX_SIZE, (1 - v) * TEX_SIZE] for u, v in fl26_uv_pts], np.float32)

print(f"FL26 landmarks: {len(fl26_names)}")

# ---------- 2. detect face landmarks on photo ----------
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BaseOptions = python.BaseOptions
FaceLandmarker = vision.FaceLandmarker
FaceLandmarkerOptions = vision.FaceLandmarkerOptions
VisionRunningMode = vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=''),
    running_mode=VisionRunningMode.IMAGE,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1,
)

img_cv = cv2.imread(PHOTO)
h, w = img_cv.shape[:2]
print(f"Photo: {w}x{h}")
# MediaPipe expects RGB; cv2 gives BGR
img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

# MediaPipe needs the model file; download it if not present
model_path = os.path.join(IN_DIR, 'face_landmarker_v2_with_blendshapes.task')
if not os.path.exists(model_path):
    import urllib.request
    url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'
    print(f"Downloading face landmarker model...")
    urllib.request.urlretrieve(url, model_path)
    print(f"Downloaded to {model_path}")

options.base_options = BaseOptions(model_asset_path=model_path)

mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
with FaceLandmarker.create_from_options(options) as landmarker:
    detection_result = landmarker.detect(mp_image)

if not detection_result.face_landmarks:
    print("FAIL: no face detected!")
    sys.exit(1)

landmarks = detection_result.face_landmarks[0]
print(f"Face detected: {len(landmarks)} landmarks")

# MediaPipe 468 landmarks indices mapping to our 19 FL26 UV landmarks
# FL26 landmark -> MediaPipe landmark index mapping
FL26_TO_MP = {
    'forehead':   10,    # forehead midpoint
    'brow_center': 9,    # brow center
    'left_eye':   159,   # left eye center
    'right_eye':  386,   # right eye center
    'nose_bridge': 6,    # nose bridge
    'nose_tip':    1,    # nose tip
    'nose_base':   2,    # nose base
    'lip_upper':   0,    # upper lip
    'lip_lower':   17,   # lower lip
    'mouth_left':  61,   # mouth left corner
    'mouth_right': 291,  # mouth right corner
    'chin':        199,  # chin
    'chin_bottom': 200,  # chin bottom
    'cheek_left':  234,  # left cheek
    'cheek_right': 454,  # right cheek
    'jaw_left':    172,  # left jaw
    'jaw_right':   397,  # right jaw
    'temple_left': 137,  # left temple
    'temple_right': 366, # right temple
}

# Extract photo landmarks
photo_pts = []
photo_names = []
for name in fl26_names:
    mp_idx = FL26_TO_MP.get(name)
    if mp_idx is not None:
        lm = landmarks[mp_idx]
        photo_pts.append((lm.x * w, lm.y * h))
        photo_names.append(name)
    else:
        print(f"WARNING: no MP mapping for {name}")

photo_pts = np.array(photo_pts, np.float32)
print(f"Photo landmarks: {len(photo_pts)}")

# Also add photo boundary anchors (8 points) for TPS stability
# compute bounding box of face + margin
bx, by = photo_pts[:, 0].mean(), photo_pts[:, 1].mean()
# scale: distance from nose to forehead ~ face height
# use a generous margin
margin = 0.5
x_min, x_max = photo_pts[:, 0].min() - (photo_pts[:, 0].max() - photo_pts[:, 0].min()) * margin, photo_pts[:, 0].max() + (photo_pts[:, 0].max() - photo_pts[:, 0].min()) * margin
y_min, y_max = photo_pts[:, 1].min() - (photo_pts[:, 1].max() - photo_pts[:, 1].min()) * margin, photo_pts[:, 1].max() + (photo_pts[:, 1].max() - photo_pts[:, 1].min()) * margin

# photo anchors (4 corners of extended face box)
photo_anchors = np.array([
    [x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max],
    [(x_min+x_max)/2, y_min], [(x_min+x_max)/2, y_max],
    [x_min, (y_min+y_max)/2], [x_max, (y_min+y_max)/2],
], np.float32)
# corresponding FL26 UV anchors (same relative positions)
uv_anchors = np.array([
    [-0.1, 1.1], [1.1, 1.1], [1.1, -0.1], [-0.1, -0.1],
    [0.5, 1.1], [0.5, -0.1], [-0.1, 0.5], [1.1, 0.5],
], np.float32)
uv_tex_anchors = np.array([[u * TEX_SIZE, (1 - v) * TEX_SIZE] for u, v in uv_anchors], np.float32)

# Combined control points
all_src = np.vstack([photo_pts, photo_anchors])
all_dst = np.vstack([fl26_tex_pts, uv_tex_anchors])

print(f"Control points: {len(all_src)} (landmarks {len(photo_pts)} + anchors {len(photo_anchors)})")

# ---------- 3. TPS warp photo -> FL26 UV ----------
from scipy.interpolate import Rbf

rbf_x = Rbf(all_dst[:, 0], all_dst[:, 1], all_src[:, 0], function='thin_plate')
rbf_y = Rbf(all_dst[:, 0], all_dst[:, 1], all_src[:, 1], function='thin_plate')

gy, gx = np.mgrid[0:TEX_SIZE, 0:TEX_SIZE].astype(np.float32)
map_x = rbf_x(gx.ravel(), gy.ravel()).reshape(TEX_SIZE, TEX_SIZE).astype(np.float32)
map_y = rbf_y(gx.ravel(), gy.ravel()).reshape(TEX_SIZE, TEX_SIZE).astype(np.float32)

# Warp
warped = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
warped_rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)

# ---------- 4. blend with base texture for neck/ear coverage ----------
base = np.array(Image.open(os.path.join(OUT_UV, 'face_southeuropean_new3.png')).convert('RGBA'))
face_alpha = np.ones((TEX_SIZE, TEX_SIZE), np.uint8) * 255

# Create mask from UV coverage (face region = u 0.15-0.85, v 0.35-0.87)
# In the target UV, the face is in this region. Outside → blend with base
# Simple: use the base texture for outside-face-region, our warped face inside
# Create a distance-based blend
from scipy.spatial import Delaunay
# Face region = convex hull of FL26 landmarks in UV space
hull = Delaunay(fl26_tex_pts)
is_face = np.zeros((TEX_SIZE, TEX_SIZE), bool)
for u in range(TEX_SIZE):
    for v in range(TEX_SIZE):
        if hull.find_simplex([[u, v]])[0] >= 0:
            is_face[v, u] = True

# Create blended result: face region = warped, outside = base
result = np.array(base)
result[is_face] = np.concatenate([warped_rgb[is_face], np.full((is_face.sum(), 1), 255, np.uint8)], axis=1)

# Also save raw warped
Image.fromarray(warped_rgb).save(os.path.join(OUT_GEN, 'custom_face_raw.png'))
Image.fromarray(result).save(os.path.join(OUT_GEN, 'custom_face_blended.png'))
print("custom_face_raw.png + custom_face_blended.png saved")

# ---------- 5. inject into avatar.unity3d (replace face_Ake pixels) ----------
import UnityPy
shutil.copy2(AVATAR, AVATAR_DST)
env_av = UnityPy.load(AVATAR_DST)
for obj in env_av.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_Ake':
            # Replace with blended RGBA
            d.set_image(Image.fromarray(result))
            d.save()
            print(f"face_Ake texture replaced with custom face (512x512 RGBA)")
            break

with open(AVATAR_DST, 'wb') as f:
    f.write(env_av.file.save())
print("avatar_custom_face.unity3d saved")

# ---------- 6. modify gamedata: PlayerAppearanceTable (byte1 30->47) ----------
import UnityPy
env_gd = UnityPy.load(GAMEDATA)
assets = {}
for obj in env_gd.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            rr = d.m_Script
            assets[d.m_Name] = rr.encode('utf-8', errors='surrogateescape') if isinstance(rr, str) else bytes(rr)

# PlayerAppearanceTable: find CustomPlayer (pid 175923), change byte1
pa = env_gd.find(f"PlayerAppearanceTable")
# Actually let's do it more carefully: find the custom player's appearance entry
pa_asset = None
for obj in env_gd.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            pa_asset = d
            break

raw = pa_asset.m_Script
if isinstance(raw, str):
    raw = raw.encode('utf-8', errors='surrogateescape')
raw = bytearray(raw)

# Find the index entry for our PID
n = struct.unpack_from("<I", raw, 0)[0]
found = False
for i in range(n):
    key, off = struct.unpack_from("<II", raw, 4 + i*8)
    if key == CUSTOM_PID:
        # Record byte1 before change
        old_b1 = raw[off + 5]
        raw[off + 5] = CUSTOM_BYTE1
        new_b1 = raw[off + 5]
        print(f"Appearance byte1 changed: {old_b1} -> {new_b1} (idx {i})")
        found = True
        break

if not found:
    print(f"ERROR: PID {CUSTOM_PID} not found in appearance table!")
    sys.exit(1)

pa_asset.m_Script = raw.decode('utf-8', errors='surrogateescape')
pa_asset.save()

# Also save gamedata bundle
shutil.copy2(GAMEDATA, BUNDLE_DST)
with open(BUNDLE_DST, 'wb') as f:
    f.write(env_gd.file.save())
print("gamedata_custom_face.unity3d saved")

# ---------- 7. Build APK ----------
BT = r'C:\FL26_Mod\android-sdk\build-tools\36.0.0'
ZIPALIGN = os.path.join(BT, 'zipalign.exe')
APKSIGNER = os.path.join(BT, 'apksigner.bat')
ADB = r'C:\FL26_Mod\android-sdk\platform-tools\adb.exe'
KEYSTORE = r'C:\FL26_Mod\build\fl26_test.keystore'

os.makedirs(os.path.dirname(AVATAR_DST), exist_ok=True)
os.makedirs(os.path.dirname(DST_APK), exist_ok=True)

with zipfile.ZipFile(SRC_APK, 'r') as zin:
    with zipfile.ZipFile(DST_APK + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/gamedata.unity3d':
                with open(BUNDLE_DST, 'rb') as f:
                    zout.writestr(item, f.read())
            elif item.filename == 'assets/bundles/avatar.unity3d':
                with open(AVATAR_DST, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
shutil.move(DST_APK + '.tmp', DST_APK)

env_vars = dict(os.environ)
env_vars['JAVA_HOME'] = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
env_vars['Path'] = env_vars['JAVA_HOME'] + r'\bin;' + env_vars.get('Path', '')
aligned = DST_APK.replace('.apk', '_aligned.apk')
subprocess.run([ZIPALIGN, '-p', '-f', '4', DST_APK, aligned], capture_output=True, env=env_vars)
os.replace(aligned, DST_APK)
r = subprocess.run([APKSIGNER, 'sign', '--ks', KEYSTORE, '--ks-pass', 'pass:fl26modtest',
                    '--ks-key-alias', 'fl26test', DST_APK], capture_output=True, text=True, env=env_vars)
print("sign:", 'OK' if r.returncode == 0 else r.stderr[-300:])

# ---------- 8. Install ----------
r = subprocess.run([ADB, 'install', '-r', DST_APK], capture_output=True, text=True, timeout=180)
print("install:", (r.stdout.strip() or r.stderr.strip())[:200])
r = subprocess.run([ADB, 'shell', 'pm', 'clear', 'com.football.soccer.league.mod'], capture_output=True, text=True, timeout=60)
print("pm clear:", r.stdout.strip())

print("\n=== DONE fl26_custom_face_test.apk ===")