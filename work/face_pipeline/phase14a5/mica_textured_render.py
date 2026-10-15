# -*- coding: utf-8 -*-
"""mica_textured_render.py — textured soft-render of the EA1-adapted MICA mesh.

Renders stage2_ea1.json (MICA shape on the game's 700-vert EA1 topology, with
EA1 UVs) with the photo bake as skin: front / 3-4 left / 3-4 right views.
No Unity needed — pure numpy rasterization with barycentric UV sampling.

Usage: recon_env python mica_textured_render.py <stage2.json> <bake.png> <out_dir> <title>
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw

stage2_p, bake_p, OUT, title = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(OUT, exist_ok=True)
d = json.load(open(stage2_p))
V = np.asarray(d['vertices'], np.float64)
_tri = np.asarray(d['triangles'])
TRI = (_tri[:, :, 0] if _tri.ndim == 3 else _tri).astype(np.int64)
UV = np.asarray(d['uv'], np.float64)
TEX = np.asarray(Image.open(bake_p).convert('RGB'), np.float64)
TS = TEX.shape[0]

NORM = (V - V.mean(0)) / (V.max(0) - V.min(0)).max()

import os as _os
W = int(_os.environ.get('RENDER_W', '560'))
def raster(Vw, W=None):
    W = W or int(_os.environ.get('RENDER_W', '560'))
    img = np.full((W, W, 3), 26.0, np.float64)
    zbuf = np.full((W, W), 1e18)
    v0, v1, v2 = Vw[TRI[:, 0]], Vw[TRI[:, 1]], Vw[TRI[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    light = np.array([0.15, 0.85, 0.5]); light /= np.linalg.norm(light)
    lam = np.clip(nn @ light, 0, 1) * 0.55 + 0.45
    t0, t1, t2 = UV[TRI[:, 0]], UV[TRI[:, 1]], UV[TRI[:, 2]]
    for i in range(len(TRI)):
        if nn[i, 1] >= 0.0:
            continue
        a, b, c = v0[i], v1[i], v2[i]
        xmin = max(int(min(a[0], b[0], c[0]) * W / 2.2 + W / 2) - 1, 0)
        xmax = min(int(max(a[0], b[0], c[0]) * W / 2.2 + W / 2) + 2, W - 1)
        ymin = max(int(min(-a[2], -b[2], -c[2]) * W / 2.2 + W / 2) - 1, 0)
        ymax = min(int(max(-a[2], -b[2], -c[2]) * W / 2.2 + W / 2) + 2, W - 1)
        if xmax <= xmin or ymax <= ymin:
            continue
        xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.5, np.arange(ymin, ymax) + 0.5)
        px = xs / W * 2.2 - 1.1
        py = (W - ys) / W * 2.2 - 1.1
        dd = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(dd) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / dd
        w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / dd
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        if not ins.any():
            continue
        u = w0 * t0[i, 0] + w1 * t1[i, 0] + w2 * t2[i, 0]
        v = w0 * t0[i, 1] + w1 * t1[i, 1] + w2 * t2[i, 1]
        tx = np.clip((u % 1.0) * TS, 0, TS - 1).astype(int)
        ty = np.clip((1 - (v % 1.0)) * TS, 0, TS - 1).astype(int)
        shade = lam[i]
        col = TEX[ty, tx] * shade
        zb_all = w0 * a[1] + w1 * b[1] + w2 * c[1]
        yy, xx = ys[ins].astype(int), xs[ins].astype(int)
        zb = zb_all[ins]
        upd = zb < zbuf[yy, xx]
        img[yy[upd], xx[upd]] = col[ins][upd]
        zbuf[yy[upd], xx[upd]] = zb[upd]
    return img.astype(np.uint8)

def yaw(Vw, deg):
    a = np.radians(deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    return Vw @ Rz.T

views = [(0, 'front'), (-40, '3_4_left'), (40, '3_4_right')]
for deg, tag in views:
    im = raster(yaw(NORM, deg))
    Image.fromarray(im).save(os.path.join(OUT, 'mica_skin_%s.png' % tag))
    print('saved', tag)
