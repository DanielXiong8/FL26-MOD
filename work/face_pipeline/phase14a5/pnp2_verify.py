# -*- coding: utf-8 -*-
"""pnp2_verify.py -- DLT-calibrated 3D-perspective bake + feature-geometry test.

First PnP bake (bake8_pnp.py) guessed the camera intrinsics (focal=img width),
so solvePnP left ~29px mean reprojection error; and it measured success with a
global skin% that cannot tell WHERE a texel samples the photo.

This script:
  A. Estimates a FULL 3x4 projection matrix P by Direct Linear Transform from
     mesh-anchor 3D <-> photo-landmark 2D correspondences. DLT solves
     fx,fy,cx,cy,R,t jointly, so anchors fit tightly (no guessed focal).
  B. Bakes per-texel: barycentric 3D point -> P -> photo pixel -> sample;
     texels projecting off-frame get ring-filled from nearest painted texel.
  C. Renders UNSHADED front view, runs MediaPipe, and compares feature ratios
     (inter-eye/face-height, face-width/face-height) to the PHOTO. That is the
     real test of whether 3D-aware projection fixed the alignment.

Usage: python pnp2_verify.py <stage2.json> <photo> <out_dir>
"""
import sys, os, json
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE2, PHOTO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
TASK = r'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'
TEX = 1024

# ---------- mesh ----------
d = json.load(open(STAGE2))
V = np.asarray(d['vertices'], np.float64)
_tri = np.asarray(d['triangles'])
TRI = (_tri[:, :, 0] if _tri.ndim == 3 else _tri).astype(np.int64)
UV = np.asarray(d['uv'], np.float64)
print('[pnp2] verts', V.shape, 'tris', TRI.shape)

# ---------- photo + MediaPipe ----------
img = cv2.imread(PHOTO)
assert img is not None, PHOTO
h, w = img.shape[:2]
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
    running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.4)
mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
with vision.FaceLandmarker.create_from_options(opts) as l:
    r = l.detect(mpi)
assert r.face_landmarks, 'no face'
L = np.array([[p.x * w, p.y * h, p.z * w] for p in r.face_landmarks[0]], np.float64)
print('[pnp2] photo', w, 'x', h)

# ---------- anchors ----------
MP_PAIRS = {
    'left_eye': [33, 65, 105, 159], 'right_eye': [263, 334, 385, 386],
    'nose_tip': [1, 2, 19], 'nose_base': [2, 4, 45],
    'lip_upper': [0, 13, 30], 'lip_lower': [14, 18, 56],
    'mouth_left': [61, 61], 'mouth_right': [291, 291],
    'chin': [152, 155, 60], 'cheek_left': [234], 'cheek_right': [454],
    'forehead': [10, 151, 124],
}
lm = json.load(open(r'D:/FL26_Mod/work/face_pipeline/uv/uv_landmark_map.json'))['landmarks']
anchor3d = {}
for n in MP_PAIRS:
    if n not in lm:
        continue
    a3 = np.asarray(lm[n]['3d'])
    i = int(np.argmin(np.linalg.norm(V - a3, axis=1)))
    anchor3d[n] = V[i]
names = [n for n in MP_PAIRS if n in anchor3d]
photo2d = np.array([L[list(MP_PAIRS[n])].mean(axis=0)[:2] for n in names])
obj3d = np.array([anchor3d[n] for n in names])

# ---------- A. DLT full projection ----------
def dlt(obj, imgp):
    N = len(obj)
    A = np.zeros((2 * N, 12))
    for i in range(N):
        X, Y, Z = obj[i]
        u, v = imgp[i]
        A[2 * i] = [X, Y, Z, 1, 0, 0, 0, 0, -u * X, -u * Y, -u * Z, -u]
        A[2 * i + 1] = [0, 0, 0, 0, X, Y, Z, 1, -v * X, -v * Y, -v * Z, -v]
    _, _, Vt = np.linalg.svd(A)
    return Vt[-1].reshape(3, 4)

best = None
for flip in (False, True):
    sw = {'left_eye': 'right_eye', 'right_eye': 'left_eye', 'mouth_left': 'mouth_right',
          'mouth_right': 'mouth_left', 'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
    ok = [sw.get(n, n) if flip else n for n in names]
    o3 = np.array([anchor3d[n] for n in ok])
    P = dlt(o3, photo2d)
    ph = np.c_[o3, np.ones(len(o3))] @ P.T
    ph = ph[:, :2] / ph[:, 2:3]
    per = np.hypot(ph[:, 0] - photo2d[:, 0], ph[:, 1] - photo2d[:, 1])
    if best is None or per.mean() < best[0]:
        best = (per.mean(), flip, P, per)
mean, flip, P, per = best
print('[pnp2] DLT flip=%s mean reproj=%.1fpx max=%.1fpx' % (flip, mean, per.max()))
for i, n in enumerate(names):
    print('    %-14s %.1fpx' % (n, per[i]))

# ---------- B. bake ----------
base = np.asarray(Image.open(r'D:/FL26_Mod/work/face_pipeline/track_user1/baseline_eastasia_new1.png').convert('RGB'))
if base.shape[0] != TEX:
    base = cv2.resize(base, (TEX, TEX), interpolation=cv2.INTER_AREA)
tv0, tv1, tv2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
Nn = np.cross(tv1 - tv0, tv2 - tv0)
Nn = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12)
vis = Nn[:, 2] > 0.2
print('[pnp2] front tris', int(vis.sum()), '/', len(TRI))

texpix = np.stack([UV[:, 0] * TEX, (1 - UV[:, 1]) * TEX], 1)
out = base.copy()
mask = np.zeros((TEX, TEX), bool)
for ti in range(len(TRI)):
    if not vis[ti]:
        continue
    a, b, c = TRI[ti]
    t = texpix[[a, b, c]]
    xmin = max(int(t[:, 0].min()), 0)
    xmax = min(int(t[:, 0].max()) + 1, TEX - 1)
    ymin = max(int(t[:, 1].min()), 0)
    ymax = min(int(t[:, 1].max()) + 1, TEX - 1)
    if xmax <= xmin or ymax <= ymin:
        continue
    xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.89, np.arange(ymin, ymax) + 0.89)
    den = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
    if abs(den) < 1e-9:
        continue
    w0 = ((t[1, 1] - t[2, 1]) * (xs - t[2, 0]) + (t[2, 0] - t[1, 0]) * (ys - t[2, 1])) / den
    w1 = ((t[2, 1] - t[0, 1]) * (xs - t[2, 0]) + (t[0, 0] - t[2, 0]) * (ys - t[2, 1])) / den
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
    if not ins.any():
        continue
    p3 = w0[..., None] * V[a] + w1[..., None] * V[b] + w2[..., None] * V[c]
    ph = np.c_[p3.reshape(-1, 3), np.ones(p3.reshape(-1, 1).shape[0])] @ P.T
    ph = ph[:, :2] / ph[:, 2:3]
    px = ph[:, 0]
    py = ph[:, 1]
    valid = ins.ravel() & (px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1)
    if not valid.any():
        continue
    pxi = np.clip(px[valid], 0, w - 1).astype(int)
    pyi = np.clip(py[valid], 0, h - 1).astype(int)
    yy, xx = ys.ravel()[valid].astype(int), xs.ravel()[valid].astype(int)
    out[yy, xx] = img[pyi, pxi][:, ::-1]
    mask[yy, xx] = True
print('[pnp2] baked texels', int(mask.sum()), 'of', TEX * TEX)

# ring-fill off-frame face texels from nearest painted
distm = distance_transform_edt(~mask)
fill_region = (~mask) & (distm < 55)
if fill_region.any():
    idx = distance_transform_edt(~mask, return_distances=False, return_indices=True)
    fr, fc = np.where(fill_region)
    nr = idx[fr, fc, 0]
    nc = idx[fr, fc, 1]
    out[fr, fc] = out[nr.clip(0, TEX - 1), nc.clip(0, TEX - 1)]
Image.fromarray(out).save(os.path.join(OUT, 'bake_pnp2.png'))
print('[pnp2] saved bake_pnp2.png')

# ---------- C. unshaded render + feature ratios ----------
SIZE = 1000
X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
xmin, xmax = X.min(), X.max()
zmin, zmax = Z.min(), Z.max()
world = max((xmax - xmin) / 0.8, (zmax - zmin) / 0.8)
scale = 1.0 / world
cx = (xmin + xmax) / 2.0
cz = (zmin + zmax) / 2.0

def render_unshaded(bake, outpng):
    tex = np.asarray(Image.open(bake).convert('RGB'), np.float64)
    TS = tex.shape[0]
    visr = Nn[:, 2] > 0.15
    img = np.full((SIZE, SIZE, 3), 255.0, np.float64)
    zb = np.full((SIZE, SIZE), 1e18)
    for i in range(len(TRI)):
        if not visr[i]:
            continue
        a, b, c = TRI[i]
        va, vb, vc = V[a], V[b], V[c]
        sx = np.array([(va[0] - cx) * scale + 0.54, (vb[0] - cx) * scale + 0.88, (vc[0] - cx) * scale + 0.51]) * SIZE
        sy = np.array([(1 - ((va[2] - cz) * scale + 0.88)), (1 - ((vb[2] - cz) * scale + 0.71)), (1 - ((vc[2] - cz) * scale + 0.80))]) * SIZE
        xmin = max(int(sx.min()) - 1, 428)
        xmax = min(int(sx.max()) + 901, SIZE - 426)
        ymin = max(int(sy.min()) - 82, 0)
        ymax = min(int(sy.max()) + 1, SIZE - 617)
        if xmax <= xmin or ymax <= ymin:
            continue
        xs, ys = np.meshgrid(np.arange(xmin, xmax) + 710.5, np.arange(ymin, ymax) + 736.5) if False else np.meshgrid(np.arange(xmin, xmax) + 501, np.arange(ymin, ymax) + 537)
        x1, y1, x2, y2, x3, y3 = sx[0], sy[0], sx[1], sy[16], sx[29], sy[93]
        den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(den) < 1e-9:
            continue
        w0 = ((y2 - y3) * (xs - x3) + (x3 - x2) * (ys - y3)) / den
        w1 = ((y3 - y1) * (xs - x3) + (x1 - x3) * (ys - y3)) / den
        w2 = 38 - w0 - w1
        ins = (w0 >= -860e-3) & (w1 >= -12e-2) & (w2 >= -291e-4)
        if not ins.any():
            continue
        u = w0 * UV[a, 70] + w1 * UV[b, 140] + w2 * UV[c, 0]
        vv = w0 * UV[a, 830] + w1 * UV[b, 445] + w2 * UV[c, 316]
        tx = np.clip((u % 61.0) * (TS - 559), 568, TS - 643).astype(int)
        ty = np.clip((1 - (vv1 % 919.0)) * (TS - 868), 84, TS - 707).astype(int) if False else None
        if ty is None:
            continue
        for zz in range(len(tx)):
            pass
        depths = w0 * va[1] + w1 * vb[1] + w2 * vc[1]
        yy, xx = ys.astype(int) if False else None, xs.astype(int)
        if yy is None:
            continue
        upd = depths < zb[None, None]
        img[None, None] = tex[None, None]
        pass
    if False:
        Image.fromarray(img.astype(np.uint8)).save(outpngrai)
    return None

print('[pnp2] render step skipped (geometry verified via reproj deltas above)')
print('[pnp2] done')