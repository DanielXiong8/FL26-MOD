# -*- coding: utf-8 -*-
# track_d_photo.py - Photo -> TPS warp -> face_southeuropean_new3 injection (verified Track D path)
# Stages: photo -> 468 landmarks -> 19 FL26 UV control points + anchors -> Rbf TPS warp
#         -> blend over baseline texture -> set_image -> APK -> sign
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

PHOTO = r'C:\Users\Lenovo\OneDrive\Desktop\111.webp'
IN_DIR = r'C:\FL26_Mod\work\face_pipeline'
WORK = os.path.join(IN_DIR, 'track_d')
UV_DIR = os.path.join(IN_DIR, 'uv')
BASELINE = os.path.join(WORK, 'baseline_southeuropean_new3.png')
PHOTO_PNG = os.path.join(WORK, 'photo_111.png')

TEX_SIZE = 512
TARGET = "assets/models/player2021/textures/face/face_southeuropean_new3.png"
SRC = r'C:\FL26_Mod\build\avatar.unity3d'
AVATAR_OUT = r'C:\FL26_Mod\build\avatar_trackd_photo.unity3d'
SRC_APK = r'C:\FL26_Mod\build\base_debuggable2.apk'
APK_OUT = r'C:\FL26_Mod\build\base_trackd_photo.apk'

# ---------- 1. FL26 UV landmarks ----------
with open(os.path.join(UV_DIR, 'uv_landmark_map.json')) as f:
    lm_data = json.load(f)
fl26_uv = {k: v['uv'] for k, v in lm_data['landmarks'].items()}
fl26_names = list(fl26_uv.keys())
fl26_tex_pts = np.array([[u*TEX_SIZE, (1-v)*TEX_SIZE] for u, v in fl26_uv.values()], np.float32)

FL26_TO_MP = {
    'forehead': 10, 'brow_center': 9, 'left_eye': 159, 'right_eye': 386,
    'nose_bridge': 6, 'nose_tip': 1, 'nose_base': 2, 'lip_upper': 0, 'lip_lower': 17,
    'mouth_left': 61, 'mouth_right': 291, 'chin': 199, 'chin_bottom': 200,
    'cheek_left': 234, 'cheek_right': 454, 'jaw_left': 172, 'jaw_right': 397,
    'temple_left': 137, 'temple_right': 366,
}

# ---------- 2. detect landmarks ----------
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

img = cv2.imread(PHOTO_PNG)
if img is None:
    img = cv2.imread(PHOTO)
h, w = img.shape[:2]
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

model_path = os.path.join(IN_DIR, 'face_landmarker_v2_with_blendshapes.task')
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=model_path),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
with vision.FaceLandmarker.create_from_options(options) as landmarker:
    res = landmarker.detect(mp_image)
if not res.face_landmarks:
    print("FAIL: no face detected"); sys.exit(1)
landmarks = res.face_landmarks[0]
print(f"Face detected: {len(landmarks)} landmarks, photo {w}x{h}")

photo_pts = []
kept = []
for name in fl26_names:
    idx = FL26_TO_MP.get(name)
    if idx is not None:
        lm = landmarks[idx]
        photo_pts.append((lm.x*w, lm.y*h))
        kept.append(name)
photo_pts = np.array(photo_pts, np.float32)
dst_pts = np.array([[fl26_uv[n][0]*TEX_SIZE, (1-fl26_uv[n][1])*TEX_SIZE] for n in kept], np.float32)

# boundary anchors
bx = photo_pts[:,0].mean(); margin = 0.5
xr = photo_pts[:,0].max()-photo_pts[:,0].min()
yr = photo_pts[:,1].max()-photo_pts[:,1].min()
x_min,x_max = photo_pts[:,0].min()-xr*margin, photo_pts[:,0].max()+xr*margin
y_min,y_max = photo_pts[:,1].min()-yr*margin, photo_pts[:,1].max()+yr*margin
photo_anchors = np.array([[x_min,y_min],[x_max,y_min],[x_max,y_max],[x_min,y_max],
    [(x_min+x_max)/2,y_min],[(x_min+x_max)/2,y_max],[x_min,(y_min+y_max)/2],[x_max,(y_min+y_max)/2]],np.float32)
uv_anchors = np.array([[-0.1,1.1],[1.1,1.1],[1.1,-0.1],[-0.1,-0.1],
    [0.5,1.1],[0.5,-0.1],[-0.1,0.5],[1.1,0.5]],np.float32)
uv_tex_anchors = np.array([[u*TEX_SIZE,(1-v)*TEX_SIZE] for u,v in uv_anchors],np.float32)

all_src = np.vstack([photo_pts, photo_anchors])
all_dst = np.vstack([dst_pts, uv_tex_anchors])
print(f"Control points: {len(all_src)}")

# ---------- 3. TPS warp ----------
from scipy.interpolate import Rbf
rbf_x = Rbf(all_dst[:,0], all_dst[:,1], all_src[:,0], function='thin_plate')
rbf_y = Rbf(all_dst[:,0], all_dst[:,1], all_src[:,1], function='thin_plate')
gy, gx = np.mgrid[0:TEX_SIZE,0:TEX_SIZE].astype(np.float32)
map_x = rbf_x(gx.ravel(),gy.ravel()).reshape(TEX_SIZE,TEX_SIZE).astype(np.float32)
map_y = rbf_y(gx.ravel(),gy.ravel()).reshape(TEX_SIZE,TEX_SIZE).astype(np.float32)
warped = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
cv2.imwrite(os.path.join(WORK,'warped_111.png'), warped)
print("warped saved")

# ---------- 4. blend over baseline ----------
base = np.array(Image.open(BASELINE).convert('RGB'))
# elliptical face mask from landmark extents (in texture coords, padded)
cx, cy = dst_pts[:,0].mean(), dst_pts[:,1].mean()
rx = max((dst_pts[:,0].max()-dst_pts[:,0].min())/2*1.9, 60)
ry = max((dst_pts[:,1].max()-dst_pts[:,1].min())/2*1.9, 60)
mask = np.zeros((TEX_SIZE,TEX_SIZE), np.float32)
cv2.ellipse(mask, (int(cx),int(cy)), (int(rx),int(ry)), 0, 0, 360, 1.0, -1)
mask = cv2.GaussianBlur(mask, (31,31), 0)[...,None]
blended = (warped.astype(np.float32)*mask + base.astype(np.float32)*(1-mask)).astype(np.uint8)
Image.fromarray(blended).save(os.path.join(WORK,'custom_face_111.png'))
print("blended saved")

# ---------- 5. inject ----------
import UnityPy
env = UnityPy.load(SRC)
tex = env.container[TARGET].read()
tex.set_image(Image.fromarray(blended))
tex.save()
with open(AVATAR_OUT,'wb') as f:
    f.write(env.file.save(packer="original"))
# verify
env2 = UnityPy.load(AVATAR_OUT)
t2 = env2.container[TARGET].read().image
diff = np.abs(np.array(t2.convert('RGB'),np.float32)-blended.astype(np.float32)).mean()
print(f"inject verify: mean abs diff = {diff:.2f} (should be small)")
print("AVATAR ->", AVATAR_OUT)

# ---------- 6. APK ----------
import zipfile
with zipfile.ZipFile(SRC_APK) as zin, zipfile.ZipFile(APK_OUT,'w') as zout:
    for item in zin.infolist():
        if item.filename == 'assets/bundles/avatar.unity3d':
            zout.writestr(item, open(AVATAR_OUT,'rb').read())
        else:
            zout.writestr(item, zin.read(item.filename))
print("APK ->", APK_OUT)
