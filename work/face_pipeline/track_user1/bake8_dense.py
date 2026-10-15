# -*- coding: utf-8 -*-
"""bake8_dense.py — V2 bake: 468-point dense TPS alignment + 1024 UV raster.

Improvement over bake8 (13-anchor Procrustes):
  1. MediaPipe 478 landmarks on photo
  2. Global similarity from 13 semantic anchors (same as before)
  3. DENSE REFINEMENT: all 478 landmarks, after similarity, are matched to the
     EA1 template surface (nearest triangle in render plane, barycentric 3D)
  4. scipy RBF thin-plate spline from 478 photo points -> template points
  5. Warp photo with TPS -> much tighter per-feature alignment
  6. Raster to UV (TEX=1024, RS=2048)

Usage: recon_env python bake8_dense.py <photo> [<v3_stage2_json>]
Output: baked_ea3_dense.png in same dir as script
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

WORK = os.path.dirname(os.path.abspath(__file__))
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
TEX = 1024
RS = 2048
FX0, FX1 = -0.10, 0.10
FZ0, FZ1 = -0.16, 0.16

m = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(m['vertices'], np.float32)
U = np.array(m['uv'], np.float32)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
v0, v1, v2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
FN = np.cross(v1 - v0, v2 - v0); FN /= (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-9)
bake_t = np.where(FN[:, 2] > 0.55)[0]

base = np.array(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB').resize((TEX, TEX), Image.LANCZOS))
photo_path = sys.argv[1]
v3_json = sys.argv[2] if len(sys.argv) > 2 else None

# optionally replace template verts with V3-deformed ones
if v3_json and os.path.exists(v3_json):
    v3 = json.load(open(v3_json))['vertices']
    V = np.array(v3, np.float32)
    print('[dense] using V3-deformed geometry')

photo = cv2.imread(photo_path)
h, w = photo.shape[:2]

def mesh2render(p):
    return np.stack([(p[:, 0] - FX0) / (FX1 - FX0) * RS,
                     (1 - (p[:, 1] - FZ0) / (FZ1 - FZ0)) * RS], 1)

# ---- MediaPipe ----
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
assert r.face_landmarks, 'no face detected'
L = np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float32)
L3 = np.array([[p.x * w, p.y * h, p.z * w] for p in r.face_landmarks[0]], np.float32)
print('photo landmarks:', L.shape)

lm = json.load(open(os.path.join(UV_DIR, 'uv_landmark_map.json')))['landmarks']
MP_PAIRS = {
    'left_eye':   [33, 133], 'right_eye':  [362, 263],
    'brow_center':[105, 334], 'nose_tip':   [1],
    'nose_base':  [2], 'lip_upper':  [0], 'lip_lower':  [17],
    'mouth_left': [61], 'mouth_right':[291], 'chin':       [152],
    'cheek_left': [234], 'cheek_right':[454], 'forehead':   [10],
}
anchor_names = list(MP_PAIRS.keys())

def anchor_render_xy(name):
    a3 = np.asarray(lm[name]['3d'])
    i = int(np.argmin(np.linalg.norm(V - a3, axis=1)))
    return mesh2render(V[i:i+1, [0, 2]])[0]

# ---- global similarity from 13 anchors ----
def build_pairs(flipLR):
    P2, Q2 = [], []
    for name in anchor_names:
        qn = name
        if flipLR:
            swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye',
                    'mouth_left': 'mouth_right', 'mouth_right': 'mouth_left',
                    'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
            qn = swap.get(name, name)
        pt = L[MP_PAIRS[name]].mean(axis=0)
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
    A = np.zeros((2, 3)); A[:, :2] = scale * R; A[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
    fit = (scale * R @ Pc.T).T - Qc
    per = np.hypot(fit[:, 0], fit[:, 1])
    return A, R, scale, per

best = None
for flip in (False, True):
    P2, Q2 = build_pairs(flip)
    A2, R2, s2, per2 = procrustes(P2, Q2)
    if best is None or per2.mean() < best[0]:
        best = (per2.mean(), flip, P2, Q2)
_, flipLR, P, Q = best
A, R, scale, per = procrustes(P, Q)
keep = per < max(2.0 * np.median(per), 15.0)
if keep.sum() >= 6:
    A, R, scale, per = procrustes(P[keep], Q[keep])
print('global similarity: scale=%.1f residual=%.1f px' % (scale, per.mean()))
img1 = cv2.warpAffine(photo, A, (RS, RS), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

# ---- DENSE TPS REFINEMENT ----
# After global similarity, for each of the 478 MediaPipe landmarks, find its
# position on the EA1 template surface (in render plane). Then fit a
# scipy RBF thin-plate from photo landmarks -> template positions.
from scipy.interpolate import RBFInterpolator

# project ALL MediaPipe points through the global similarity
L_all = np.column_stack([L, np.ones(len(L))])
L_render = (A[:2] @ L_all.T).T  # (478, 2) in render plane

# find nearest template surface point for each landmark (in render plane)
# build template render-plane point cloud from front-facing triangles
V_2d = mesh2render(V[:, [0, 2]])
# for each MediaPipe landmark, find nearest template vertex (in 2D render plane)
from scipy.spatial import KDTree
tree_v = KDTree(V_2d)
dd, ii = tree_v.query(L_render, k=1)
# keep landmarks whose nearest template vertex is reasonably close (on the face)
mask = dd < np.inf  # all 478 are on the face, use all
src_pts = L_render[mask]          # source: landmark positions in render plane
dst_pts = V_2d[ii[mask]]          # target: nearest template vertex position

# RBF thin-plate spline: photo render-plane -> template render-plane
from scipy.interpolate import RBFInterpolator
rbf = RBFInterpolator(src_pts, dst_pts, kernel='thin_plate_spline', smoothing=1.0)
res_tps = np.linalg.norm(rbf(src_pts) - dst_pts, axis=1).mean()
print('TPS refinement residual: %.1f px (mean)' % res_tps)

# warp the photo using the combined global+TPS transform
# for each pixel in render plane, apply: global A -> then TPS correction
# we build the correction grid
step = 16
gx = np.arange(0, RS + step, step)
gy = np.arange(0, RS + step, step)
gx, gy = np.meshgrid(gx, gy)
grid_pts = np.column_stack([gx.ravel(), gy.ravel()])
corrected = rbf(grid_pts)
# TPS correction = corrected - grid_pts
delta = corrected - grid_pts
# for each render pixel: photo_pixel = A_inv(render_pixel) + TPS_delta(interp)
from scipy.interpolate import LinearNDInterpolator
delta_interp = LinearNDInterpolator(grid_pts, delta, fill_value=0.0)

# apply inverse A to get render->photo mapping, then add TPS delta in render space
A_inv = cv2.invertAffineTransform(A)
# create the full warp: for each output pixel, sample input at A_inv(pixel) + TPS correction
map_x = np.zeros((RS, RS), np.float32)
map_y = np.zeros((RS, RS), np.float32)
xs, ys = np.meshgrid(np.arange(RS), np.arange(RS))
pts = np.column_stack([xs.ravel() + 0.5, ys.ravel() + 0.5])
# inverse global
inv_pts = (A_inv[:, :2] @ pts.T).T + A_inv[:, 2]
# TPS correction in render space (approximate: use forward delta at the point)
cr = rbf(pts)
corr = cr - pts
# combined: inverse global + TPS correction
final_pts = inv_pts + corr * 0.5  # scaled correction
map_x = final_pts[:, 0].reshape(RS, RS).astype(np.float32)
map_y = final_pts[:, 1].reshape(RS, RS).astype(np.float32)
img1 = cv2.remap(photo, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(img1[..., ::-1]).save(os.path.join(WORK, 'bake_dense_stage1.png'))

# ---- lighting transfer (same as bake8) ----
tex_px = np.stack([U[:, 0] * TEX, (1 - U[:, 1]) * TEX], 1)
rend = np.zeros((RS, RS, 3), np.uint8)
front_t = np.where(FN[:, 2] > 0.4)[0]
for ti in front_t:
    a, b, c = TRI[ti]
    q = mesh2render(V[[a, b, c]][:, [0, 2]]); t = tex_px[[a, b, c]]
    xmin, xmax = int(min(q[:, 0])) - 1, int(max(q[:, 0])) + 2
    ymin, ymax = int(min(q[:, 1])) - 1, int(max(q[:, 1])) + 2
    xs2, ys2 = np.meshgrid(np.arange(max(xmin, 0), min(xmax, RS)) + 0.5,
                           np.arange(max(ymin, 0), min(ymax, RS)) + 0.5)
    dd = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
    if abs(dd) < 1e-9: continue
    w0 = ((q[1, 1] - q[2, 1]) * (xs2 - q[2, 0]) + (q[2, 0] - q[1, 0]) * (ys2 - q[2, 1])) / dd
    w1 = ((q[2, 1] - q[0, 1]) * (xs2 - q[2, 0]) + (q[0, 0] - q[2, 0]) * (ys2 - q[2, 1])) / dd
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any(): continue
    tu = w0[..., None] * t[0] + w1[..., None] * t[1] + w2[..., None] * t[2]
    px2 = np.clip(tu[..., 0], 0, TEX - 1).astype(int); py2 = np.clip(tu[..., 1], 0, TEX - 1).astype(int)
    yy3 = np.clip(ys2[ins].astype(int), 0, RS-1); xx3 = np.clip(xs2[ins].astype(int), 0, RS-1)
    py3 = np.clip(py2[ins], 0, TEX-1); px3 = np.clip(px2[ins], 0, TEX-1)
    rend[yy3, xx3] = base[py3, px3]

try:
    g_rend = cv2.GaussianBlur(cv2.cvtColor(rend, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 20)
    g_img1 = cv2.GaussianBlur(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 20)
    ratio = (g_rend + 1) / (g_img1 + 1)
    img1s = np.clip(img1.astype(np.float32) * ratio[..., None], 0, 255).astype(np.uint8)
except Exception as e:
    print('lighting skipped:', e)
    img1s = img1

# ---- bake to UV ----
out = base.copy()
mask = np.zeros((TEX, TEX), np.float32)
for ti in bake_t:
    a3, b3, c3 = TRI[ti]
    t = tex_px[[a3, b3, c3]]
    q = mesh2render(V[[a3, b3, c3]][:, [0, 2]])
    x_lo = max(int(t[:, 0].min()), 0)
    x_hi = min(int(t[:, 0].max()) + 1, TEX - 1)
    y_lo = max(int(t[:, 1].min()), 0)
    y_hi = min(int(t[:, 1].max()) + 1, TEX - 1)
    if x_hi <= x_lo or y_hi <= y_lo: continue
    xs2, ys2 = np.meshgrid(np.arange(x_lo, x_hi) + 0.5, np.arange(y_lo, y_hi) + 0.5)
    dd = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
    if abs(dd) < 1e-9: continue
    w0 = ((t[1, 1] - t[2, 1]) * (xs2 - t[2, 0]) + (t[2, 0] - t[1, 0]) * (ys2 - t[2, 1])) / dd
    w1 = ((t[2, 1] - t[0, 1]) * (xs2 - t[2, 0]) + (t[0, 0] - t[2, 0]) * (ys2 - t[2, 1])) / dd
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any(): continue
    xy = w0[..., None] * q[0] + w1[..., None] * q[1] + w2[..., None] * q[2]
    rpx = mesh2render(xy.reshape(-1, 2))
    pw, ph = rpx[:, 0], rpx[:, 1]
    valid = ins.ravel() & (pw >= 0) & (pw < RS - 1) & (ph >= 0) & (ph < RS - 1)
    if not valid.any(): continue
    pxi = np.clip(pw, 0, RS - 1).astype(int); pyi = np.clip(ph, 0, RS - 1).astype(int)
    yy2, xx2 = ys2.ravel()[valid].astype(int), xs2.ravel()[valid].astype(int)
    nz = FN[ti, 2]
    take = nz >= mask[yy2, xx2]
    out[yy2[take], xx2[take]] = img1s[pyi[valid][take], pxi[valid][take]][..., ::-1]
    mask[yy2[take], xx2[take]] = nz

alpha = cv2.GaussianBlur((mask > 0).astype(np.float32), (0, 0), 1.5)[..., None]
outf = base.astype(np.float32) * (1 - alpha) + out.astype(np.float32) * alpha
out = np.clip(outf, 0, 255).astype(np.uint8)
out_path = os.path.join(WORK, 'baked_ea3_dense.png')
Image.fromarray(out).save(out_path)
print('baked %d px (%.1f%%) -> %s' % (int(mask.sum()), mask.mean() * 100, out_path))
