# -*- coding: utf-8 -*-
"""soft_render_v3.py -- game-quality-approximating preview renderer.

Upgrades over v2 (whose flat per-triangle shading + nearest sampling made the
preview look far rougher than the real game):
  1. per-pixel smooth shading: vertex normals interpolated barycentrically
  2. bilinear texture sampling (no texel blocks)
  3. 2x supersampling + LANCZOS downscale (anti-aliasing)

Usage: python soft_render_v3.py <stage2.json> <bake.png> <out_dir> <tag> [size]
"""
import sys, os, json
import numpy as np
from PIL import Image

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
STAGE2, BAKE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SIZE = int(sys.argv[5]) if len(sys.argv) > 5 else 800
SS = 2
W = SIZE * SS
os.makedirs(OUT, exist_ok=True)

d = json.load(open(STAGE2))
V = np.asarray(d['vertices'], np.float64)
_tri = np.asarray(d['triangles'])
TRI = (_tri[:, :, 0] if _tri.ndim == 3 else _tri).astype(np.int64)
UV = np.asarray(d['uv'], np.float64)
TEX = np.asarray(Image.open(BAKE).convert('RGB'), np.float64)
TS = TEX.shape[0]

# vertex normals (area-weighted)
VN = np.zeros_like(V)
tv0, tv1, tv2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
FN = np.cross(tv1 - tv0, tv2 - tv0)
for k in range(3):
    np.add.at(VN, TRI[:, k], FN)
VN /= (np.linalg.norm(VN, axis=1, keepdims=True) + 1e-12)

X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
xmin, xmax = X.min(), X.max()
zmin, zmax = Z.min(), Z.max()
world = max((xmax - xmin) / 0.8, (zmax - zmin) / 0.8)
scl = 1.0 / world
cx = (xmin + xmax) / 2.0
cz = (zmin + zmax) / 2.0
ymin = Z.min()


def project(Vs):
    sxp = (Vs[:, 0] - cx) * scl + 0.5
    syp = 1.0 - ((Vs[:, 2] - cz) * scl + 0.5)
    return np.stack([np.clip(sxp * W, 0, W - 1), np.clip(syp * W, 0, W - 1)], 1), Vs[:, 2]


light = np.array([0.15, -0.85, 0.50]); light = light / np.linalg.norm(light)
vis = (np.cross(tv1 - tv0, tv2 - tv0)[:, 1] < 0)


def render_view(Vr, tag):
    VNr = VN.copy()
    if tag != 'front':
        a = np.radians(38 if tag.endswith('right') else -38)
        Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        Vr = Vr @ Rz.T
        VNr = VN @ Rz.T
    vr0, vr1, vr2 = Vr[TRI[:, 0]], Vr[TRI[:, 1]], Vr[TRI[:, 2]]
    img = np.full((W, W, 3), 26.0, np.float64)
    zbuf = np.full((W, W), 1e18)
    for i in range(len(TRI)):
        if not vis[i]:
            continue
        ia, ib, ic = TRI[i]
        pa, pb, pc = project(np.stack([Vr[ia], Vr[ib], Vr[ic]]))[0]
        xmn = max(int(min(pa[0], pb[0], pc[0])) - 1, 0)
        xmx = min(int(max(pa[0], pb[0], pc[0])) + 2, W - 1)
        ymn = max(int(min(pa[1], pb[1], pc[1])) - 1, 0)
        ymx = min(int(max(pa[1], pb[1], pc[1])) + 2, W - 1)
        if xmx <= xmn or ymx <= ymn:
            continue
        xs, ys = np.meshgrid(np.arange(xmn, xmx) + 0.5, np.arange(ymn, ymx) + 0.5)
        x1, y1, x2, y2, x3, y3 = pa[0], pa[1], pb[0], pb[1], pc[0], pc[1]
        den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(den) < 1e-9:
            continue
        w0 = ((y2 - y3) * (xs - x3) + (x3 - x2) * (ys - y3)) / den
        w1 = ((y3 - y1) * (xs - x3) + (x1 - x3) * (ys - y3)) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        if not ins.any():
            continue
        w0m, w1m, w2m = w0[ins], w1[ins], w2[ins]
        yy, xx = ys[ins], xs[ins]
        # perspective-ish depth (linear ok for small tris)
        depth = w0m * Vr[ia, 2] + w1m * Vr[ib, 2] + w2m * Vr[ic, 2]
        # smooth normal
        nx = w0m * VNr[ia, 0] + w1m * VNr[ib, 0] + w2m * VNr[ic, 0]
        ny = w0m * VNr[ia, 1] + w1m * VNr[ib, 1] + w2m * VNr[ic, 1]
        nz = w0m * VNr[ia, 2] + w1m * VNr[ib, 2] + w2m * VNr[ic, 2]
        shade = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1) * 0.65 + 0.42
        # bilinear UV sample
        u = w0m * UV[ia, 0] + w1m * UV[ib, 0] + w2m * UV[ic, 0]
        v = w0m * UV[ia, 1] + w1m * UV[ib, 1] + w2m * UV[ic, 1]
        fx = np.clip((u % 1.0) * TS - 0.5, 0, TS - 1.001)
        fy = np.clip((1 - (v % 1.0)) * TS - 0.5, 0, TS - 1.001)
        x0i = fx.astype(np.int64); y0i = fy.astype(np.int64)
        dx = (fx - x0i)[..., None]; dy = (fy - y0i)[..., None]
        c00 = TEX[y0i, x0i]; c10 = TEX[y0i, np.minimum(x0i + 1, TS - 1)]
        c01 = TEX[np.minimum(y0i + 1, TS - 1), x0i]; c11 = TEX[np.minimum(y0i + 1, TS - 1), np.minimum(x0i + 1, TS - 1)]
        col = (c00 * (1 - dx) * (1 - dy) + c10 * dx * (1 - dy) + c01 * (1 - dx) * dy + c11 * dx * dy)
        col = col * shade[..., None]
        yyi, xxi = yy.astype(np.int64), xx.astype(np.int64)
        upd = depth < zbuf[yyi, xxi]
        img[yyi[upd], xxi[upd]] = col[upd]
        zbuf[yyi[upd], xxi[upd]] = depth[upd]
    im8 = np.clip(img, 0, 255).astype(np.uint8)
    out = Image.fromarray(im8).resize((SIZE, SIZE), Image.LANCZOS)
    out.save(os.path.join(OUT, 'v3_%s.png' % tag))
    print('[v3] saved', tag)


render_view(V, 'front')
render_view(V, '3_4_left')
render_view(V, '3_4_right')
print('[v3] done -> %s' % OUT)