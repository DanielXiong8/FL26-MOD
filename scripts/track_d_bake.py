# -*- coding: utf-8 -*-
# track_d_bake.py - Mesh-guided photo baking onto face_southeuropean_new3
# Fixes: silver face (only front-face UV islands overwritten), double nose
#        (UV from real mesh triangles), bent brows (similarity transform, no free TPS)
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

WORK = r'C:\FL26_Mod\work\face_pipeline\track_d'
UV_DIR = r'C:\FL26_Mod\work\face_pipeline\uv'
BASELINE = os.path.join(WORK, 'baseline_southeuropean_new3.png')
PHOTO_PNG = os.path.join(WORK, 'photo_111.png')
TEX = 512
TARGET = "assets/models/player2021/textures/face/face_southeuropean_new3.png"
MIRROR = len(sys.argv) > 1 and sys.argv[1] == 'mirror'

# ---------- mesh ----------
top = json.load(open(os.path.join(UV_DIR, 'mesh_topology.json')))
uvj = json.load(open(os.path.join(UV_DIR, 'mesh_uv.json')))
V = np.array([[v['x'], v['y'], v['z']] for v in top['vertices']], np.float32)
N = np.array([[v['nx'], v['ny'], v['nz']] for v in top['vertices']], np.float32)
Tr = top['triangles']
if isinstance(Tr[0], dict):
    T = np.array([[t['v0'], t['v1'], t['v2']] for t in Tr], np.int64)
else:
    T = np.array(Tr, np.int64)
U = np.array([[p['u'], p['v']] for p in uvj['uv']], np.float32)
assert top['vertex_count'] == uvj['uv_count']

# front-face vertices: normal points +z
front_v = N[:, 2] > 0.4
Vf = V[front_v]
nose_i = int(np.argmax(V[:, 2]))
nose = V[nose_i, :2]
# eye clusters: front verts above nose, |x| large
cand = np.where(front_v & (V[:, 1] > nose[1] + 0.01) & (V[:, 1] < nose[1] + 0.06) & (np.abs(V[:, 0]) > 0.03))[0]
eyeL = V[cand[np.argmin(V[cand, 0])], :2]   # mesh x- side
eyeR = V[cand[np.argmax(V[cand, 0])], :2]   # mesh x+ side
chin_c = V[np.where(front_v)[0][np.argmin(V[front_v, 1])], :2]
print(f"mesh anchors: eyeL={eyeL.round(3)} eyeR={eyeR.round(3)} nose={nose.round(3)} chin={chin_c.round(3)}")

# ---------- photo landmarks ----------
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
img = cv2.imread(PHOTO_PNG)
h, w = img.shape[:2]
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
opts = vision.FaceLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=os.path.join(UV_DIR, '..', 'face_landmarker_v2_with_blendshapes.task')),
    running_mode=vision.RunningMode.IMAGE, num_faces=1)
mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
with vision.FaceLandmarker.create_from_options(opts) as lmk:
    res = lmk.detect(mpi)
L = res.face_landmarks[0]
P = {k: np.array([L[i].x * w, L[i].y * h], np.float32)
     for k, i in dict(eyeL=159, eyeR=386, nose=1, chin=199).items()}
print("photo anchors:", {k: v.round(1).tolist() for k, v in P.items()})

# correspondence: photo eye on image-left -> mesh side chosen by MIRROR flag
# (mirror flag flips horizontal mapping; default assumes image-left -> mesh x-)
if MIRROR:
    src = np.array([P['eyeR'], P['eyeL'], P['nose'], P['chin']], np.float32)
else:
    src = np.array([P['eyeL'], P['eyeR'], P['nose'], P['chin']], np.float32)
dst = np.array([eyeL, eyeR, nose, chin_c], np.float32)
M, _ = cv2.estimateAffinePartial2D(src, dst)
print("similarity M:\n", M.round(4))

# ---------- bake ----------
base = np.array(Image.open(BASELINE).convert('RGB'))
out = base.copy()
mask = np.zeros((TEX, TEX), np.float32)  # coverage mask for reporting
pix_uv = U * TEX
pix_uv[:, 1] = (1.0 - U[:, 1]) * TEX

# front triangles: average nz > 0.4
tri_nz = N[T].mean(axis=1)[:, 2]
front_t = np.where(tri_nz > 0.4)[0]
print(f"front triangles: {len(front_t)}/{len(T)}")
inv = cv2.invertAffineTransform(M)

for ti in front_t:
    a, b, c = T[ti]
    p0, p1, p2 = pix_uv[a], pix_uv[b], pix_uv[c]
    xmin = max(int(np.floor(min(p0[0], p1[0], p2[0]))), 0)
    xmax = min(int(np.ceil(max(p0[0], p1[0], p2[0]))), TEX - 1)
    ymin = max(int(np.floor(min(p0[1], p1[1], p2[1]))), 0)
    ymax = min(int(np.ceil(max(p0[1], p1[1], p2[1]))), TEX - 1)
    if xmax < xmin or ymax < ymin:
        continue
    xs, ys = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
    d = (p1[1]-p2[1])*(p0[0]-p2[0]) + (p2[0]-p1[0])*(p0[1]-p2[1])
    if abs(d) < 1e-9:
        continue
    w0 = ((p1[1]-p2[1])*(xs-p2[0]) + (p2[0]-p1[0])*(ys-p2[1])) / d
    w1 = ((p2[1]-p0[1])*(xs-p2[0]) + (p0[0]-p2[0])*(ys-p2[1])) / d
    w2 = 1 - w0 - w1
    inside = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not inside.any():
        continue
    xy = w0[..., None]*V[a,:2] + w1[..., None]*V[b,:2] + w2[..., None]*V[c,:2]
    # xy (mesh coords) -> photo pixel via inverse affine
    ph = inv @ np.stack([xy[..., 0].ravel(), xy[..., 1].ravel(), np.ones(xy[..., 0].size)])
    px = np.clip(ph[0].reshape(xs.shape), 0, w-1).astype(np.int32)
    py = np.clip(ph[1].reshape(xs.shape), 0, h-1).astype(np.int32)
    sel = inside
    out[ys[sel].astype(int), xs[sel].astype(int)] = img[py[sel], px[sel]][:, ::-1]
    mask[ys[sel].astype(int), xs[sel].astype(int)] = 1.0

print(f"baked pixels: {int(mask.sum())} ({mask.sum()/TEX/TEX*100:.1f}% of texture)")
Image.fromarray(out).save(os.path.join(WORK, f'baked_111{"_mirror" if MIRROR else ""}.png'))
np.save(os.path.join(WORK, f'bake_mask{"_mirror" if MIRROR else ""}.npy'), mask)
print("saved baked preview")
