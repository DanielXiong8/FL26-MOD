# -*- coding: utf-8 -*-
"""track_d_bake8.py - principled re-bake: semantic-anchor similarity align + NATIVE mesh UV raster.

Fixes vs bake7 (which produced skewed baked_ea2):
  1. Photo alignment: Procrustes SIMILARITY (rotation+uniform scale+translation) from
     14+ semantic correspondences (MediaPipe idx -> FL26 uv_landmark_map anchors).
     No TPS, no RANSAC over noisy 468 pts -> no asymmetric eye skew.
  2. Texel rasterization: mesh NATIVE UV (mesh_ea1.json 'uv') directly, the same layout
     baseline_eastasia_new1.png uses. No empirical u(x)/v(y) mapping (bake7's error source).
  3. Lighting/shading transfer retained from bake7 (baseline low-freq luminance ratio).
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

import sys as _sys
WORK = os.path.dirname(os.path.abspath(_sys.argv[0]))
PHOTO = _sys.argv[1]
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
TEX = 1024
RS = 2048
FX0, FX1 = -0.10, 0.10
FZ0, FZ1 = -0.16, 0.16   # mesh is Z-up (z range 0.306 = vertical); render plane = (x, z)

m = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(m['vertices'], np.float32)
# V3 RE-BAKE: if BAKE_V3_JSON is set, replace the template vertices with the
# V3-deformed ones (MICA shape on EA1 topology) so the photo is re-projected
# through the DEFORMED geometry — painted features follow the new positions
# (eye spacing / jaw width stay aligned with the skull).
import os as _os
_v3p = _os.environ.get('BAKE_V3_JSON')
if _v3p:
    import json as _json
    _v3 = _json.load(open(_v3p))['vertices']
    assert len(_v3) == len(V), 'V3 vertex count mismatch'
    V = np.array(_v3, np.float32)
    print('[bake8-v3] geometry replaced: %s' % _v3p)
U = np.array(m['uv'], np.float32)          # native game UV (v: 1=top in our diag convention)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
v0, v1, v2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
FN = np.cross(v1 - v0, v2 - v0); FN /= (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-9)
bake_t = np.where((FN[:, 2] > (float(__import__('os').environ.get('BAKE_NZ0', '0.06')))) & (FN[:, 2] < (float(__import__('os').environ.get('BAKE_NZ1', '0.75')))) & (FN[:, 1] < float(__import__('os').environ.get('BAKE_NY', '0.15'))))[0]

base = np.array(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB').resize((TEX, TEX), Image.LANCZOS))
photo = cv2.imread(PHOTO)
h, w = photo.shape[:2]

def mesh2render(p):
    # p given as (x, z) vertical profile
    return np.stack([(p[:, 0] - FX0) / (FX1 - FX0) * RS,
                     (1 - (p[:, 1] - FZ0) / (FZ1 - FZ0)) * RS], 1)

# ---------------- MediaPipe detection on photo ----------------
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
model = os.path.join(UV_DIR, '..', 'face_landmarker_v2_with_blendshapes.task')
rgb = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=model),
    running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.5)
mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
with vision.FaceLandmarker.create_from_options(opts) as l:
    r = l.detect(mpi)
assert r.face_landmarks, 'photo face detection failed'
L = np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float32)
print('photo landmarks:', L.shape)

# ---------------- semantic correspondences ----------------
# MediaPipe idx pairs -> uv_landmark_map anchor (mesh 3d -> native UV via barycentric-ish nearest vert)
# ---- STEP-2 anchors: photo MediaPipe <-> SKELETON targets (from baseline clusters) ----
# Step 1 located the game mesh's true feature positions by detecting the baseline
# texture's own eye/nose/mouth clusters and mapping them to owning vertices.
SK = json.load(open(os.path.join(WORK, 'skel_anchors.json')))
SK_TEX = 512
def skel_render_xy(name):
    tx, ty = SK[name]
    u, v = tx / SK_TEX, 1 - ty / SK_TEX
    i = int(np.argmin((U[:, 0] - u) ** 2 + (U[:, 1] - v) ** 2))
    return mesh2render(V[i:i+1, [0, 2]])[0]
MP2 = {'left_eye': [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
       'nose': [98, 327, 2], 'mouth': [0, 13, 14, 17]}
anchor_names = list(MP2.keys())
def build_pairs(flipLR):
    P2, Q2 = [], []
    for name in anchor_names:
        pt = L[MP2[name]].mean(axis=0)
        qn = name
        if flipLR:
            qn = {'left_eye': 'right_eye', 'right_eye': 'left_eye'}.get(name, name)
        P2.append(pt[:2]); Q2.append(skel_render_xy(qn))
    return np.array(P2, np.float64), np.array(Q2, np.float64)
def procrustes(P, Q):
    Pc, Qc = P - P.mean(0), Q - Q.mean(0)
    H = Pc.T @ Qc
    Us, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ Us.T)) or 1.0
    R = Vt.T @ np.diag([1.0, d]) @ Us.T
    scale = (S * d).sum() / (Pc ** 2).sum()
    A = np.zeros((2, 3))
    A[:, :2] = scale * R
    A[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
    fit = (scale * R @ Pc.T).T - Qc
    per = np.hypot(fit[:, 0], fit[:, 1])
    return A, R, scale, per
best = None
for flip in (False, True):
    P2, Q2 = build_pairs(flip)
    A2, R2, s2, per2 = procrustes(P2, Q2)
    print('flipLR=%s residual=%.1f px scale=%.1f' % (flip, per2.mean(), s2))
    if best is None or per2.mean() < best[0]: best = (per2.mean(), flip, P2, Q2)
_, flipLR, P, Q = best
A, R, scale, per = procrustes(P, Q)
for n, p in zip(anchor_names, per): print('  %-10s %.1f px' % (n, p))
print('similarity: scale=%.1f rot=%.2f deg, residual mean=%.1f px' %
      (scale, np.degrees(np.arctan2(R[1, 0], R[0, 0])), per.mean()))

img1 = cv2.warpAffine(photo, A, (RS, RS), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
Image.fromarray(img1[..., ::-1]).save(os.path.join(WORK, 'bake8w_stage1.png'))
# face-hull validity mask in render space (kills background pollution)
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
_P = np.asarray(L[FACE_OVAL], np.float64)
_hull = np.c_[_P, np.ones(len(_P))] @ np.asarray(A, np.float64).T
HULL = np.zeros((RS, RS), np.uint8)
cv2.fillPoly(HULL, [(_hull).astype(np.int32)], 1)
HULL = cv2.erode(HULL, np.ones((3, 3), np.uint8))

# ---------------- lighting/shading transfer (same as bake7) ----------------
# baseline reference render: raster native-UV front triangles of baseline texture
tex_px = np.stack([U[:, 0] * TEX, (1 - U[:, 1]) * TEX], 1)
rend = np.zeros((RS, RS, 3), np.uint8)
front_t = np.where(FN[:, 2] > (float(__import__('os').environ.get('BAKE_NZ', '0.06'))))[0]
for ti in front_t:
    a, b, c = TRI[ti]
    q = mesh2render(V[[a, b, c]][:, [0, 2]]); t = tex_px[[a, b, c]]
    xmin, xmax = int(min(q[:, 0])) - 1, int(max(q[:, 0])) + 2
    ymin, ymax = int(min(q[:, 1])) - 1, int(max(q[:, 1])) + 2
    xs, ys = np.meshgrid(np.arange(max(xmin, 0), min(xmax, RS)) + 0.5,
                         np.arange(max(ymin, 0), min(ymax, RS)) + 0.5)
    dd = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
    if abs(dd) < 1e-9: continue
    w0 = ((q[1, 1] - q[2, 1]) * (xs - q[2, 0]) + (q[2, 0] - q[1, 0]) * (ys - q[2, 1])) / dd
    w1 = ((q[2, 1] - q[0, 1]) * (xs - q[2, 0]) + (q[0, 0] - q[2, 0]) * (ys - q[2, 1])) / dd
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any(): continue
    tu = w0[..., None] * t[0] + w1[..., None] * t[1] + w2[..., None] * t[2]
    px = np.clip(tu[..., 0], 0, TEX - 1).astype(int); py = np.clip(tu[..., 1], 0, TEX - 1).astype(int)
    rend[ys[ins].astype(int), xs[ins].astype(int)] = base[py[ins], px[ins]]

g_rend = cv2.GaussianBlur(cv2.cvtColor(rend, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 20)
g_img1 = cv2.GaussianBlur(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 20)
has_rend = cv2.GaussianBlur((rend.sum(2) > 12).astype(np.float32), (0, 0), 8)
ratio = (g_rend + 1) / (g_img1 + 1)
ratio = np.where(has_rend > 0.04, np.clip(ratio, 0.55, 1.9), 1.0).astype(np.float32)
img1s = np.clip(img1.astype(np.float32) * ratio[..., None], 0, 255).astype(np.uint8)
Image.fromarray(img1s[..., ::-1]).save(os.path.join(WORK, 'bake8w_stage2_shaded.png'))

def render_to_img1(px):
    return np.stack([px[..., 0], px[..., 1]], -1)   # identity: photo already in render space

# ---- STEP-2b: MLS local affine (per-triangle, skeleton-anchor guided) ----
SK_TEX = 512
SKP = {'left_eye': L[[33,65,133,159]].mean(0)[:2], 'right_eye': L[[362,385,263,386]].mean(0)[:2],
       'nose': L[[98,327,2]].mean(0)[:2], 'mouth': L[[0,13,14,17]].mean(0)[:2],
       'left_brow': L[[105]].mean(0)[:2], 'right_brow': L[[334]].mean(0)[:2]}
SKR = {}
for _n, _p in SKP.items():
    _tx, _ty = SK[_n]
    _i = int(np.argmin((U[:,0]-_tx/SK_TEX)**2 + (U[:,1]-(1-_ty/SK_TEX))**2))
    SKR[_n] = mesh2render(V[_i:_i+1, [0,2]])[0]
A_R = np.array([SKR[k] for k in SKP])
A_P = np.array([SKP[k] for k in SKP])
X_A = np.c_[A_R, np.ones(len(A_R))]
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
PH_MASK = np.zeros((h, w), np.uint8)
cv2.fillPoly(PH_MASK, [L[FACE_OVAL].astype(np.int32)], 1)
PH_MASK = cv2.erode(PH_MASK, np.ones((17,17), np.uint8))
def mls_M(qc):
    d2 = ((A_R - qc)**2).sum(1)
    wgt = np.sqrt(1.0/(d2 + 3e4))
    M, *_ = np.linalg.lstsq(X_A * wgt[:,None], A_P * wgt[:,None], rcond=None)
    return M
ratio_field = np.where(has_rend > 0.04, np.clip((g_rend + 1) / (g_img1 + 1), 0.55, 1.9), 1.0).astype(np.float32)

# ---------------- bake: NATIVE UV triangle raster ----------------
out = base.copy()
mask = np.zeros((TEX, TEX), np.float32)
for ti in bake_t:
    a, b, c = TRI[ti]
    t = tex_px[[a, b, c]]                                   # native UV texel
    q = V[[a, b, c]][:, [0, 2]]                                 # mesh (x, z)
    r = mesh2render(q)                                      # render space = warped photo space
    xmin, xmax = max(int(t[:, 0].min()), 0), min(int(t[:, 0].max()) + 1, TEX - 1)
    ymin, ymax = max(int(t[:, 1].min()), 0), min(int(t[:, 1].max()) + 1, TEX - 1)
    if xmax <= xmin or ymax <= ymin: continue
    xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.5, np.arange(ymin, ymax) + 0.5)
    dd = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
    if abs(dd) < 1e-9: continue
    w0 = ((t[1, 1] - t[2, 1]) * (xs - t[2, 0]) + (t[2, 0] - t[1, 0]) * (ys - t[2, 1])) / dd
    w1 = ((t[2, 1] - t[0, 1]) * (xs - t[2, 0]) + (t[0, 0] - t[2, 0]) * (ys - t[2, 1])) / dd
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any(): continue
    xy = w0[..., None] * q[0] + w1[..., None] * q[1] + w2[..., None] * q[2]
    rpx = mesh2render(xy.reshape(-1, 2))
    qc = r.mean(0)
    M = mls_M(qc)
    pw_ph = np.c_[rpx, np.ones(len(rpx))] @ M
    pw, ph = pw_ph[:, 0], pw_ph[:, 1]
    valid = ins.ravel() & (pw >= 0) & (pw < w - 1) & (ph >= 0) & (ph < h - 1) & (PH_MASK[np.clip(ph, 0, h - 1).astype(int), np.clip(pw, 0, w - 1).astype(int)] > 0)
    if not valid.any(): continue
    pxi = np.clip(pw, 0, w - 1).astype(int); pyi = np.clip(ph, 0, h - 1).astype(int)
    yy, xx = ys.ravel()[valid].astype(int), xs.ravel()[valid].astype(int)
    nz = FN[ti, 2]
    take = nz >= mask[yy, xx]
    shade = ratio_field[np.clip(rpx[valid][take][:, 1].astype(int), 0, RS - 1), np.clip(rpx[valid][take][:, 0].astype(int), 0, RS - 1)][:, None]
    out[yy[take], xx[take]] = np.clip(photo[pyi[valid][take], pxi[valid][take]] * shade, 0, 255)[..., ::-1]
    mask[yy[take], xx[take]] = nz

from scipy.ndimage import distance_transform_edt as _edt
_fill = _edt(~(mask > 0), return_distances=False, return_indices=True)
_fd = _edt(~(mask > 0))
_fr, _fc = np.where((mask == 0) & (_fd < 75))
mask[_fr, _fc] = 1.0
out[_fr, _fc] = out[_fill[0, _fr, _fc], _fill[1, _fr, _fc]]
alpha = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 1.5)[..., None]
outf = base.astype(np.float32) * (1 - alpha) + out.astype(np.float32) * alpha
out = np.clip(outf, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(WORK, 'baked_wide.png'))
print('baked %d px (%.1f%%) -> baked_wide.png' % (int(mask.sum()), mask.mean() * 100))
