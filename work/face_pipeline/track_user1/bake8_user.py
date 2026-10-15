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
UV_DIR = r'C:\FL26_Mod\work\face_pipeline\uv'
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
bake_t = np.where(FN[:, 2] > 0.55)[0]

base = np.array(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB'))
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
lm = json.load(open(os.path.join(UV_DIR, 'uv_landmark_map.json')))['landmarks']
# anchor positions in render plane: use nearest mesh vertex of each anchor 3d
anchor_names = ['left_eye', 'right_eye', 'brow_center', 'nose_tip', 'nose_base',
                'lip_upper', 'lip_lower', 'mouth_left', 'mouth_right', 'chin',
                'cheek_left', 'cheek_right', 'forehead']
MP_PAIRS = {                     # mp idx pairs averaged -> anchor
    'left_eye':   [33, 133],     # left eye outer/inner corner
    'right_eye':  [362, 263],
    'brow_center':[105, 334],    # mid of both brows (avg of 2 pts each side)
    'nose_tip':   [1],
    'nose_base':  [2],
    'lip_upper':  [0],
    'lip_lower':  [17],
    'mouth_left': [61],
    'mouth_right':[291],
    'chin':       [152],
    'cheek_left': [234],
    'cheek_right':[454],
    'forehead':   [10],
}
def anchor_render_xy(name):
    a3 = np.asarray(lm[name]['3d'])
    i = int(np.argmin(np.linalg.norm(V - a3, axis=1)))
    return mesh2render(V[i:i+1, [0, 2]])[0]   # (x, z)

# handedness: mesh 'left'=anatomical left=viewer RIGHT; mp naming follows the image.
# Try both pairings, keep the one with lower Procrustes residual.
def build_pairs(flipLR):
    P2, Q2 = [], []
    for name in anchor_names:
        qn = name
        if flipLR:
            swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye',
                    'mouth_left': 'mouth_right', 'mouth_right': 'mouth_left',
                    'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
            qn = swap.get(name, name)
        idxs = MP_PAIRS[name]
        pt = L[idxs].mean(axis=0)
        q = anchor_render_xy(qn)
        P2.append(pt); Q2.append(q)
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
# robust refit: drop anchors with residual > 2x median, refit
A, R, scale, per = procrustes(P, Q)
keep = per < max(2.0 * np.median(per), 15.0)
print('per-anchor px:', {n: round(float(p), 1) for n, p in zip(anchor_names, per)})
if keep.sum() >= 6:
    A, R, scale, per = procrustes(P[keep], Q[keep])
    print('refit on %d/%d inliers: residual=%.1f px' % (keep.sum(), len(P), per.mean()))
flipLR_keep = keep
print('similarity: scale=%.1f rot=%.2f deg, residual mean=%.1f px' %
      (scale, np.degrees(np.arctan2(R[1, 0], R[0, 0])), per.mean()))

img1 = cv2.warpAffine(photo, A, (RS, RS), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(img1[..., ::-1]).save(os.path.join(WORK, 'bake8_stage1.png'))

# ---------------- lighting/shading transfer (same as bake7) ----------------
# baseline reference render: raster native-UV front triangles of baseline texture
tex_px = np.stack([U[:, 0] * TEX, (1 - U[:, 1]) * TEX], 1)
rend = np.zeros((RS, RS, 3), np.uint8)
front_t = np.where(FN[:, 2] > 0.4)[0]
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
ratio = (g_rend + 1) / (g_img1 + 1)
img1s = np.clip(img1.astype(np.float32) * ratio[..., None], 0, 255).astype(np.uint8)
Image.fromarray(img1s[..., ::-1]).save(os.path.join(WORK, 'bake8_stage2_shaded.png'))

def render_to_img1(px):
    return np.stack([px[..., 0], px[..., 1]], -1)   # identity: photo already in render space

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
    pw, ph = rpx[:, 0], rpx[:, 1]
    valid = ins.ravel() & (pw >= 0) & (pw < RS - 1) & (ph >= 0) & (ph < RS - 1)
    if not valid.any(): continue
    pxi = np.clip(pw, 0, RS - 1).astype(int); pyi = np.clip(ph, 0, RS - 1).astype(int)
    yy, xx = ys.ravel()[valid].astype(int), xs.ravel()[valid].astype(int)
    nz = FN[ti, 2]
    take = nz >= mask[yy, xx]
    out[yy[take], xx[take]] = img1s[pyi[valid][take], pxi[valid][take]][..., ::-1]
    mask[yy[take], xx[take]] = nz

alpha = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 1.5)[..., None]
outf = base.astype(np.float32) * (1 - alpha) + out.astype(np.float32) * alpha
out = np.clip(outf, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(WORK, 'baked_ea3.png'))
print('baked %d px (%.1f%%) -> baked_ea3.png' % (int(mask.sum()), mask.mean() * 100))
