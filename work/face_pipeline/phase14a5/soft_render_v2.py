# -*- coding: utf-8 -*-
"""soft_render_v2.py -- auto-framed textured soft-renderer for the Z-up EA1 face shell.

The old mica_textured_render.py hardcoded a projection that left the face as a
0.2% sliver. This one auto-frames the mesh by its own bounds (Z-up axes) so the
face fills ~88% of the canvas, then rasterizes with barycentric UV sampling and
a z-buffer on the depth (Y) axis.

Usage: python soft_render_v2.py <stage2.json> <bake.png> <out_dir> <title> [size]
Outputs: <out_dir>/v2_front.png, v2_3_4_left.png, v2_3_4_right.png
"""
import sys, os, json
import numpy as np
from PIL import Image

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STAGE2, BAKE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SIZE = int(sys.argv[5]) if len(sys.argv) > 5 else 700
try:
    SIZE = int(os.environ.get('RENDER_W', str(SIZE)))
except Exception:
    pass
os.makedirs(OUT, exist_ok=True)

d = json.load(open(STAGE2))
V = np.asarray(d['vertices'], np.float64)
_tri = np.asarray(d['triangles'])
TRI = (_tri[:, :, 0] if _tri.ndim == 3 else _tri).astype(np.int64)
UV = np.asarray(d['uv'], np.float64)
TEX = np.asarray(Image.open(BAKE).convert('RGB'), np.float64)
TS = TEX.shape[0]

# auto-framing -- MEASURED convention (vertex data + FN mean [0,-0.32,-0.06]):
# Z = vertical (Z-up), Y = face direction (face points -Y), X = left/right.
# Camera at -Y looking +Y; screen-x = X, screen-y = -Z (Z up), depth = Y (smaller = closer).
X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
xmin, xmax = X.min(), X.max()
zmin, zmax = Z.min(), Z.max()
xr = max(xmax - xmin, 1e-6)
zr = max(zmax - zmin, 1e-6)
marg = 0.10
world = max(xr / (1 - 2 * marg), zr / (1 - 2 * marg))
scale = 1.0 / world
cx = (xmin + xmax) / 2.0
cz = (zmin + zmax) / 2.0
ymin = Y.min()
ymax = Y.max()
yr = max(ymax - ymin, 1e-6)


def project(Vs):
    sxp = (Vs[:, 0] - cx) * scale + 0.5
    syp = 1.0 - ((Vs[:, 2] - cz) * scale + 0.5)   # Z up -> invert for screen y
    px = np.clip(sxp * SIZE, 0, SIZE - 1)
    py = np.clip(syp * SIZE, 0, SIZE - 1)
    depth = (Vs[:, 1] - ymin) / yr
    return np.stack([px, py], 1), depth


tv0, tv1, tv2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
Nn = np.cross(tv1 - tv0, tv2 - tv0)
Nn = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12)
viewdir = np.array([0, -1, 0.0])
vertical = (Nn * viewdir[None, :]).sum(1) > 0.0
visible = vertical
print('[v2] front tris', int(visible.sum()), '/', len(TRI))

img = np.full((SIZE, SIZE, 3), 18.0, np.float64)
zbuf = np.full((SIZE, SIZE), 1e9)
light = np.array([0.15, -0.85, 0.50])
light = light / np.linalg.norm(light)
ut0, ut1, ut2 = UV[TRI[:, 0]], UV[TRI[:, 1]], UV[TRI[:, 2]]


def raster_face(Vr, Nnr, vis, imgout, zbufout):
    for i in range(len(TRI)):
        if not vis[i]:
            continue
        a, b, c = TRI[i]
        vA, vB, vC = Vr[a], Vr[b], Vr[c]
        pa, pb, pc = project(np.stack([vA, vB, vC]))[0]
        xmin = max(int(min(pa[0], pb[0], pc[0])) - 1, 0)
        xmax = min(int(max(pa[0], pb[0], pc[0])) + 2, SIZE - 1)
        ymin = max(int(min(pa[1], pb[1], pc[1])) - 1, 0)
        ymax = min(int(max(pa[1], pb[1], pc[1])) + 2, SIZE - 1)
        if xmax <= xmin or ymax <= ymin:
            continue
        xs, ys = np.meshgrid(np.arange(xmin, xmax) + 0.6, np.arange(ymin, ymax) + 0.6)
        x1, y1 = pa[0], pa[1]
        x2, y2 = pb[0], pb[1]
        x3, y3 = pc[0], pc[1]
        den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(den) < 1e-9:
            continue
        w0 = ((y2 - y3) * (xs - x3) + (x3 - x2) * (ys - y3)) / den
        w1 = ((y3 - y1) * (xs - x3) + (x1 - x3) * (ys - y3)) / den
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        if not ins.any():
            continue
        depths = w0 * vA[1] + w1 * vB[1] + w2 * vC[1]
        u = w0 * ut0[i, 0] + w1 * ut1[i, 0] + w2 * ut2[i, 0]
        vv = w0 * ut0[i, 1] + w1 * ut1[i, 1] + w2 * ut2[i, 1]
        tx = np.clip((u % 1.0) * (TS - 1), 0, TS - 1).astype(np.int64)
        ty = np.clip((1 - (vv % 1.0)) * (TS - 1), 0, TS - 1).astype(np.int64)
        shade = np.clip(Nnr[i] @ light, 0, 1) * 0.72 + 0.30
        col = TEX[ty, tx] * shade
        yy, xx = ys.astype(np.int64), xs.astype(np.int64)
        upd = depths < zbufout[yy, xx]
        imgout[yy[upd], xx[upd]] = col[upd]
        zbufout[yy[upd], xx[upd]] = depths[upd]


raster_face(V, Nn, visible, img, zbuf)
print('[v2] painted pixels:', int((zbuf < 1e8).sum()))

for roty, tag in [(0, 'front'), (-38, '3_4_left'), (38, '3_4_right')]:
    if roty:
        a = np.radians(roty)
        Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        Vr = V @ Rz.T
    else:
        Vr = V
    tvr0, tvr1, tvr2 = Vr[TRI[:, 0]], Vr[TRI[:, 1]], Vr[TRI[:, 2]]
    Nnr = np.cross(tvr1 - tvr0, tvr2 - tvr0)
    Nnr = Nnr / (np.linalg.norm(Nnr, axis=1, keepdims=True) + 1e-12)
    visr = (Nnr[:, 1] < 0)
    imgr = np.full((SIZE, SIZE, 3), 18.0, np.float64)
    zbufr = np.full((SIZE, SIZE), 1e9)
    raster_face(Vr, Nnr, visr, imgr, zbufr)
    img8 = np.clip(imgr, 18, 252).astype(np.uint8)
    Image.fromarray(img8).save(os.path.join(OUT, 'v2_%s.png' % tag))
    print('[v2] saved', tag)

print('[v2] done -> %s' % OUT)