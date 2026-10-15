# -*- coding: utf-8 -*-
"""bake8_pnp.py — 3D-PERSPECTIVE-aware re-bake (breaks the 2D-similarity limit).

ROOT CAUSE the old bake8_user.py could not fix:
  bake8_user.py fits a 2D Procrustes SIMILARITY (4 DOF) and then samples every
  texel by ORTHOGRAPHIC projection of the mesh's (x, z) onto the warped photo.
  That discards DEPTH (y). A face is a 3D object shot with a perspective camera:
  the nose protrudes toward the lens, eye spacing and jaw width scale DIFFERENTLY
  in depth. No similarity / resolution / extra anchors can fix it -- features get
  re-projected by the game's 3D camera and land in the wrong place. Hence
  "贴皮 = 换个人" even when the 骨相 (the personalized mesh) matches.

THIS FILE uses a real 3D->2D camera (solvePnP) built from the personalized mesh
  anchors <-> photo pixel landmarks:
    1. MediaPipe FaceLandmarker -> 2D pixel anchors (in the PHOTO's own frame).
    2. For each semantic anchor, its 3D position ON the personalized stage2 mesh.
    3. solvePnP (EPnP, planar-robust) -> R, t (extrinsics) with a fixed K.
    4. Per texel inside a front-facing triangle: barycentric 3D point -> project
       through the camera -> sample the photo. Depth now participates, so the
       nose / cheeks / jaw land exactly where the camera saw them.
    5. Normal-based visibility cull; points projecting outside the photo keep the
       baseline texture (we only have a front view, so sides/back are untouched).

Usage: python bake8_pnp.py <stage2.json> <photo> <out_dir> [title]
       env: BAKE_TEX (default 1024), PNP_FOCAL (default = photo width)
Outputs: <out_dir>/bake_pnp.png, <out_dir>/pnp_debug.png (anchor reprojection)
"""
import sys, os, json
import numpy as np
import cv2
from PIL import Image

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE2, PHOTO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
TASK = r'D:\FL26_Mod\work\face_pipeline\face_landmarker_v2_with_blendshapes.task'

TEX = int(os.environ.get('BAKE_TEX', '1024'))
KEEP_BASELINE = os.environ.get('KEEP_BASELINE', '1') != '0'

# ---------- load personalized mesh (stage2) ----------
s2 = json.load(open(STAGE2))
V = np.asarray(s2['vertices'], np.float64)          # (700,3) Z-up, ~shell units
UV = np.asarray(s2['uv'], np.float64)
tri_raw = np.asarray(s2['triangles'])
if tri_raw.ndim == 3:
    TRI = tri_raw[:, :, 0]          # (1254,3) from [[vi,ui],[vj,uj],[vk,uk]]
else:
    TRI = tri_raw                   # already (1254,3)
print('[pnp] verts', V.shape, 'tris', TRI.shape, 'uv', UV.shape)

# ---------- baseline texture ----------
base_png = os.path.join(r'D:\FL26_Mod\work\face_pipeline\track_user1', 'baseline_eastasia_new1.png')
base = np.asarray(Image.open(base_png).convert('RGB'))
if base.shape[0] != TEX:
    base = cv2.resize(base, (TEX, TEX), interpolation=cv2.INTER_AREA)
print('[pnp] baseline', base.shape, 'KEEP_BASELINE=', KEEP_BASELINE)

# ---------- MediaPipe 468 landmarks on the photo ----------
img = cv2.imread(PHOTO)
assert img is not None, 'cannot read ' + PHOTO
h, w = img.shape[:2]
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
opts = vision.FaceLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=TASK),
    running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.4)
mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
with vision.FaceLandmarker.create_from_options(opts) as l:
    r = l.detect(mpi)
assert r.face_landmarks, 'no face in photo'
L = np.array([[p.x * w, p.y * h, p.z * w] for p in r.face_landmarks[0]], np.float64)
print('[pnp] MediaPipe landmarks in photo frame:', L.shape, '(', w, 'x', h, ')')

# ---------- anchor table: name -> mp idx list ----------
MP_PAIRS = {
    'left_eye':   [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
    'brow_center':[105, 334],          'nose_tip':  [1, 19, 2],
    'nose_base':  [2, 38, 45],         'lip_upper': [0, 13, 52],
    'lip_lower':  [17, 14, 16],        'mouth_left':[61, 184],
    'mouth_right':[291, 314],          'chin':      [152, 175, 199],
    'cheek_left': [234],               'cheek_right':[454],
    'forehead':   [10, 151, 9],
}
lm = json.load(open(os.path.join(UV_DIR, 'uv_landmark_map.json')))['landmarks']

# ---------- triangle normals ----------
tri_3d = V[TRI]
v0, v1, v2 = tri_3d[:, 0], tri_3d[:, 1], tri_3d[:, 2]
FN = np.cross(v1 - v0, v2 - v0)
FNn = FN / (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-12)
front_mask = FNn[:, 2] > 0.35
print('[pnp] front tris', int(front_mask.sum()), '/', len(TRI))

# ---------- anchor 3D on the personalized mesh (nearest template vertex) ----------
anchor_3d = {}
for n in MP_PAIRS:
    if n not in lm:
        continue
    a3 = np.asarray(lm[n]['3d'])
    i = int(np.argmin(np.linalg.norm(V - a3, axis=1)))
    anchor_3d[n] = V[i]
names = [n for n in MP_PAIRS if n in anchor_3d]
print('[pnp] anchors', names)

# ---------- photo pixel anchors (2D) ----------
photo_pix = {n: L[list(MP_PAIRS[n])].mean(axis=0)[:2] for n in names}

# ---------- intrinsics ----------
K = np.eye(3, dtype=np.float64)
FL = float(os.environ.get('PNP_FOCAL', str(w)))
K[0, 0] = K[1, 1] = FL
K[0, 2] = w / 2.0
K[1, 2] = h / 2.0
dist = np.zeros((5, 1))

def solve(flip):
    swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye',
            'mouth_left': 'mouth_right', 'mouth_right': 'mouth_left',
            'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
    obj, imgp = [], []
    for n in names:
        qn = swap.get(n, n) if flip else n
        obj.append(anchor_3d[qn])
        imgp.append(photo_pix[n])
    obj = np.asarray(obj, np.float64).reshape(-1, 3)
    imgp = np.asarray(imgp, np.float64).reshape(-1, 1, 2)
    ok, rv, tv = cv2.solvePnP(obj, imgp, K, dist, flags=cv2.SOLVEPNP_EPNP)
    if not ok:
        return None
    return rv, tv

best = None
for flip in (False, True):
    s = solve(flip)
    if s is None:
        continue
    rv, tv = s
    swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye',
            'mouth_left': 'mouth_right', 'mouth_right': 'mouth_left',
            'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
    objs = np.asarray([anchor_3d[swap.get(n, n) if flip else n] for n in names], np.float64)
    projpts, _ = cv2.projectPoints(objs.reshape(-1, 3), rv, tv, K, dist)
    projpts = projpts.reshape(-1, 2)
    pix = np.asarray([photo_pix[n] for n in names])
    per = np.hypot(projpts[:, 0] - pix[:, 0], projpts[:, 1] - pix[:, 1])
    if best is None or per.mean() < best[0]:
        best = (per.mean(), flip, rv.copy(), tv.copy(), per)
mean, flip, rv, tv, per = best
print('[pnp] chosen flip=%s  mean reproj=%.1fpx  max=%.1fpx' % (flip, mean, per.max()))
for i, n in enumerate(names):
    print('    %-14s %.1fpx' % (n, per[i]))

# ---------- per-texel 3D->photo projection bake ----------
tex_px = np.stack([UV[:, 0] * TEX, (1 - UV[:, 1]) * TEX], 1)  # (700,2) texel coords
out = base.copy()
mask = np.zeros((TEX, TEX), np.float32)

cent = tri_3d.mean(axis=1)
view = (tv.ravel()[None, :] - cent)
view = view / (np.linalg.norm(view, axis=1, keepdims=True) + 1e-12)
visible = (FNn * view).sum(axis=1) > 0.0
print('[pnp] visible tris', int(visible.sum()), '/', len(TRI))

for ti in range(len(TRI)):
    if not (front_mask[ti] and visible[ti]):
        continue
    a, b, c = TRI[ti]
    t = tex_px[[a, b, c]]
    xmin, xmax = max(int(t[:, 0].min()), 0), min(int(t[:, 0].max()) + 1, TEX - 1)
    ymin, ymax = max(int(t[:, 1].min()), 0), min(int(t[:, 1].max()) + 1, TEX - 1)
    if xmax <= xmin or ymax <= ymin:
        continue
    xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.5, np.arange(ymin, ymax) + 0.5)
    dd = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
    if abs(dd) < 1e-9:
        continue
    w0 = ((t[1, 1] - t[2, 1]) * (xs - t[2, 0]) + (t[2, 0] - t[1, 0]) * (ys - t[2, 1])) / dd
    w1 = ((t[2, 1] - t[0, 1]) * (xs - t[2, 0]) + (t[0, 0] - t[2, 0]) * (ys - t[2, 1])) / dd
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any():
        continue
    p3 = (w0[..., None] * V[a] + w1[..., None] * V[b] + w2[..., None] * V[c])
    pts = p3.reshape(-1, 3)
    pobj = pts.reshape(-1, 1, 3).astype(np.float64)
    proj, _ = cv2.projectPoints(pobj, rv, tv, K, dist)
    proj = proj.reshape(-1, 2)
    px = proj[:, 0]
    py = proj[:, 1]
    valid = ins.ravel() & (px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1)
    if not valid.any():
        continue
    pxi = np.clip(px[valid], 0, w - 1).astype(int)
    pyi = np.clip(py[valid], 0, h - 1).astype(int)
    yy, xx = ys.ravel()[valid].astype(int), xs.ravel()[valid].astype(int)
    sample = img[pyi, pxi][:, ::-1]              # BGR->RGB
    out[yy, xx] = sample
    mask[yy, xx] = 1.0

print('[pnp] baked %d texels' % int(mask.sum()))

alpha = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 1.2)[..., None]
outf = base.astype(np.float32) * (1 - alpha) + out.astype(np.float32) * alpha
out = np.clip(outf, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(OUT, 'bake_pnp.png'))
print('[pnp] saved', os.path.join(OUT, 'bake_pnp.png'))

# ---------- debug overlay ----------
dbg = img.copy()
swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye', 'mouth_left': 'mouth_right',
        'mouth_right': 'mouth_left', 'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
for i, n in enumerate(names):
    qn = swap.get(n, n) if flip else n
    obj = np.asarray([anchor_3d[qn]], np.float64).reshape(-1, 1, 3)
    pr, _ = cv2.projectPoints(obj, rv, tv, K, dist)
    pr = pr.reshape(-1, 2)
    cv2.circle(dbg, (int(pr[0]), int(pr[1])), 6, (0, 128, 255), -1)   # BLUE = reprojected 3D
    cv2.circle(dbg, (int(photo_pix[n][0]), int(photo_pix[n][1])), 8, (0, 255, 0), 2)  # GREEN = det
Image.fromarray(dbg[:, :, ::-1]).save(os.path.join(OUT, 'pnp_debug.png'))
print('[pnp] done')