# -*- coding: utf-8 -*-
# relight1.py - normal-aware de-light/re-light post-step for the golden bake.
# Replaces bake7's global low-freq ratio with a per-texel ratio parameterized by
# the mesh surface normal, so photo lighting is swapped for the game (baseline)
# lighting while high-frequency identity detail is preserved.
import sys, os, json
import numpy as np
import cv2
from PIL import Image

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
OUT = os.path.join(WORK, 'relight')
os.makedirs(OUT, exist_ok=True)

BAKE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, 'baked_1024.png')
TEX = 1024
SIG = 14.0

m = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(m['vertices'], np.float64)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
U = np.array(m['uv'], np.float64)

v0, v1, v2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
FN = np.cross(v1 - v0, v2 - v0)
FN = FN / (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-12)
front = np.where(FN[:, 2] > 0.30)[0]

bake = np.asarray(Image.open(BAKE).convert('RGB'), np.float64)
if bake.shape[0] != TEX:
    bake = cv2.resize(bake, (TEX, TEX), interpolation=cv2.INTER_AREA)
base = np.asarray(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB'), np.float64)
if base.shape[0] != TEX:
    base = cv2.resize(base, (TEX, TEX), interpolation=cv2.INTER_AREA)

tex_px = np.stack([U[:, 0] * TEX, (1 - U[:, 1]) * TEX], 1)

# painted mask = texels covered by front triangles (same rule as bake8)
mask = np.zeros((TEX, TEX), np.float32)
NX = np.zeros((TEX, TEX), np.float32)
NY = np.zeros((TEX, TEX), np.float32)
NZm = np.zeros((TEX, TEX), np.float32)
P3X = np.zeros((TEX, TEX), np.float32)
P3Y = np.zeros((TEX, TEX), np.float32)
P3Z = np.zeros((TEX, TEX), np.float32)
for ti in front:
    a, b, c = TRI[ti]
    t = tex_px[[a, b, c]]
    xmin = max(int(t[:, 0].min()), 0)
    xmax = min(int(t[:, 0].max()) + 1, TEX - 1)
    ymin = max(int(t[:, 1].min()), 0)
    ymax = min(int(t[:, 1].max()) + 1, TEX - 1)
    if xmax <= xmin or ymax <= ymin:
        continue
    xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.5, np.arange(ymin, ymax) + 0.5)
    den = (t[1, 1] - t[2, 1]) * (t[0, 0] - t[2, 0]) + (t[2, 0] - t[1, 0]) * (t[0, 1] - t[2, 1])
    if abs(den) < 1e-9:
        continue
    w0 = ((t[1, 1] - t[2, 1]) * (xs - t[2, 0]) + (t[2, 0] - t[1, 0]) * (ys - t[2, 1])) / den
    w1 = ((t[2, 1] - t[0, 1]) * (xs - t[2, 0]) + (t[0, 0] - t[2, 0]) * (ys - t[2, 1])) / den
    w2 = 1 - w0 - w1
    ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
    if not ins.any():
        continue
    yy, xx = ys[ins].astype(int), xs[ins].astype(int)
    take = FN[ti, 2] >= mask[yy, xx]
    mask[yy[take], xx[take]] = FN[ti, 2]
    NX[yy[take], xx[take]] = FN[ti, 0]
    NY[yy[take], xx[take]] = FN[ti, 1]
    NZm[yy[take], xx[take]] = FN[ti, 2]
    p3 = w0[..., None] * V[a] + w1[..., None] * V[b] + w2[..., None] * V[c]
    P3X[yy[take], xx[take]] = p3[..., 0][ins][take]
    P3Y[yy[take], xx[take]] = p3[..., 1][ins][take]
    P3Z[yy[take], xx[take]] = p3[..., 2][ins][take]

pm = mask > 0
print('front texels:', int(pm.sum()))

gl = lambda im: cv2.GaussianBlur(im, (0, 0), SIG)
bake_low = gl(cv2.cvtColor(bake.astype(np.float32), cv2.COLOR_RGB2GRAY))
base_low = gl(cv2.cvtColor(base.astype(np.float32), cv2.COLOR_RGB2GRAY))

ys, xs = np.where(pm)
ratio = base_low[ys, xs] / np.maximum(bake_low[ys, xs], 8.0)
ratio = np.clip(ratio, 0.35, 2.8)
nx, ny, nz = NX[ys, xs], NY[ys, xs], NZm[ys, xs]
A = np.stack([np.ones_like(nx), nx, ny, nz, nx * nx, ny * ny, nz * nz,
              nx * ny, ny * nz, nx * nz], 1)
wfit, *_ = np.linalg.lstsq(A, np.log(ratio), rcond=None)
fit_all = np.exp(np.clip(A @ wfit, np.log(0.35), np.log(2.8)))
resid = np.abs(np.log(ratio) - np.log(fit_all))
print('normal-field log-ratio fit: mean|res|=%.3f  px=%d' % (resid.mean(), len(ys)))

out = bake.copy()
relit = bake[ys, xs] * fit_all[:, None]
out[ys, xs] = np.clip(relit, 0, 255)
# feather the boundary like bake8
alpha = cv2.GaussianBlur(pm.astype(np.float32), (0, 0), 1.5)[..., None]
outf = bake * (1 - alpha) + out * alpha
out = np.clip(outf, 0, 255).astype(np.uint8)
Image.fromarray(out).save(os.path.join(OUT, 'baked_relight.png'))

# numeric check: low-freq match to baseline before vs after (painted area only)
bl_b = np.abs(np.log(np.maximum(bake_low[ys, xs], 8) / np.maximum(base_low[ys, xs], 8))).mean()
after_low = gl(cv2.cvtColor(out.astype(np.float32), cv2.COLOR_RGB2GRAY))
bl_a = np.abs(np.log(np.maximum(after_low[ys, xs], 8) / np.maximum(base_low[ys, xs], 8))).mean()
# high-freq detail preservation
hp_b = bake_low - cv2.GaussianBlur(bake, (0, 0), SIG)[..., :1].mean(2)
hp_a = after_low - cv2.GaussianBlur(out.astype(np.float32), (0, 0), SIG)[..., :1].mean(2)
det_b = float(np.std(bake.astype(np.float32).mean(2)[ys, xs] - bake_low[ys, xs]))
det_a = float(np.std(out.astype(np.float32).mean(2)[ys, xs] - after_low[ys, xs]))
print('low-freq |log ratio| vs baseline: before=%.3f after=%.3f (smaller=better match)' % (bl_b, bl_a))
print('high-freq detail std: before=%.2f after=%.2f (equal=identity preserved)' % (det_b, det_a))
print('saved', os.path.join(OUT, 'baked_relight.png'))
