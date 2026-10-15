# -*- coding: utf-8 -*-
# trace_eyes.py - per-pixel triangle trace of the eye screen area: which mesh
# triangles paint the dark wedges, and what UVs/texture colors they carry.
import sys, os, json
import numpy as np
from PIL import Image

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
STAGE2 = r'track_user1/stage2_sculpt.json'
BAKE = r'track_user1/baked_full.png'
d = json.load(open(STAGE2))
V = np.asarray(d['vertices'], np.float64)
_tri = np.asarray(d['triangles'])
TRI = (_tri[:, :, 0] if _tri.ndim == 3 else _tri).astype(np.int64)
UV = np.asarray(d['uv'], np.float64)
TEX = np.asarray(Image.open(BAKE).convert('RGB'), np.float64)
TS = TEX.shape[0]

# collapsed verts = identical positions (find duplicates)
from collections import defaultdict
posmap = defaultdict(list)
for i, p in enumerate(V):
    posmap[tuple(np.round(p, 6))].append(i)
collapsed_groups = [v for v in posmap.values() if len(v) > 1]
collapsed_set = set(v for g in collapsed_groups for v in g)
print('[trace] collapsed verts: %d (groups %d)' % (len(collapsed_set), len(collapsed_groups)))

X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
xmin, xmax = X.min(), X.max()
zmin, zmax = Z.min(), Z.max()
world = max((xmax - xmin) / 0.8, (zmax - zmin) / 0.8)
scl = 1.0 / world
cx = (xmin + xmax) / 2.0
cz = (zmin + zmax) / 2.0
SIZE = 800

tv0, tv1, tv2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
Nn = np.cross(tv1 - tv0, tv2 - tv0)
Nn = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12)
vis = Nn[:, 1] < 0

trace = []
for i in range(len(TRI)):
    if not vis[i]:
        continue
    a, b, c = TRI[i]
    va, vb, vc = V[a], V[b], V[c]
    def prj(p):
        return ((p[0] - cx) * scl + 0.5) * SIZE, (1 - ((p[2] - cz) * scl + 0.5)) * SIZE
    pa = np.array(prj(va)); pb = np.array(prj(vb)); pc = np.array(prj(vc))
    xmn = max(int(min(pa[0], pb[0], pc[0])) - 1, 0)
    xmx = min(int(max(pa[0], pb[0], pc[0])) + 2, SIZE - 1)
    ymn = max(int(min(pa[1], pb[1], pc[1])) - 1, 0)
    ymx = min(int(max(pa[1], pb[1], pc[1])) + 2, SIZE - 1)
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
    yy, xx = ys[ins], xs[ins]
    for _yy, _xx in zip(yy.astype(int), xx.astype(int)):
        if 280 <= _xx <= 530 and 285 <= _yy <= 360:   # both-eye screen band
            trace.append((i, _xx, _yy))

from collections import Counter
cc = Counter(t[0] for t in trace)
print('[trace] eye-band pixels: %d from %d triangles' % (len(trace), len(cc)))
uvcc = UV[TRI].mean(1)
for ti, cnt in cc.most_common(10):
    degenerate = any(v in collapsed_set for v in TRI[ti])
    print('  tri %4d px=%4d degenerate=%s uv=(%.3f,%.3f) texel=(%4d,%4d) texRGB=%s' % (
        ti, cnt, degenerate, uvcc[ti, 0], uvcc[ti, 1],
        int(uvcc[ti, 0] * TS), int((1 - uvcc[ti, 1]) * TS),
        np.round(TEX[int((1 - uvcc[ti, 1]) * TS) % TS, int(uvcc[ti, 0] * TS) % TS]).astype(int)))