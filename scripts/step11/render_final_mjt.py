# -*- coding: utf-8 -*-
"""Render MICA-adapted FL26 ea1 with baked_ea3 texture: front / 45deg / side panel.
Uses own rasterizer (no pyglet). Flat texture + simple lambert shading by normal.
"""
import json
import numpy as np
from PIL import Image, ImageDraw

ADAPT = r'D:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'
EA1 = r'D:\FL26_Mod\work\face_pipeline\uv\mesh_ea1.json'
TEX = r'D:\FL26_Mod\work\face_pipeline\track_d\baked_mjt_v1.png'
OUT = r'D:\FL26_Mod\face_benchmark\adapter\final_mjt_views_flat.png'

ad = json.load(open(ADAPT)); ea = json.load(open(EA1))
V = np.asarray(ad['vertices'], np.float64)          # MICA-adapted, Z-up, meters
TRI = np.asarray(ea['triangles'])[:, :, 0]
U = np.asarray(ea['uv'], np.float64)
v0, v1, v2 = V[TRI[:, 0]], V[TRI[:, 1]], V[TRI[:, 2]]
FN = np.cross(v1 - v0, v2 - v0); FN /= (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-9)

tex = np.asarray(Image.open(TEX).convert('RGB'))
tex_px = np.stack([U[:, 0] * 511, (1 - U[:, 1]) * 511], 1)

RS = 700
def render(yaw_deg):
    a = np.radians(yaw_deg)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Vr = V @ Rz.T
    x, z = Vr[:, 0], Vr[:, 2]     # Z-up model: vertical stays z, yaw around z
    cx, cz = x.mean(), z.mean()
    sx = (x.max() - x.min()); sz = (z.max() - z.min())
    s = 0.85 * RS / max(sx, sz)
    px = RS / 2 + (x - cx) * s
    py = RS / 2 - (z - cz) * s
    P = np.stack([px, py], 1)
    img = np.full((RS, RS, 3), 34, np.uint8)
    zbuf = np.full((RS, RS), -1e9)
    L = np.array([0.3, 0.8, 0.5]); L /= np.linalg.norm(L)
    front = np.where((FN @ np.array([0, 0, 1])) > 0.05)[0]
    shade = np.clip(FN @ L, 0.25, 1.0) * 0 + 1.0  # flat light: show the texture clearly
    for ti in front:
        i0, i1, i2 = TRI[ti]
        q = P[[i0, i1, i2]]
        zz = (z[i0] + z[i1] + z[i2]) / 3 + abs(Vr[[i0, i1, i2]][:, 1].mean())  # depth bias for yaw
        t = tex_px[[i0, i1, i2]]
        xmin, xmax = int(q[:, 0].min()) - 1, int(q[:, 0].max()) + 2
        ymin, ymax = int(q[:, 1].min()) - 1, int(q[:, 1].max()) + 2
        xs, ys = np.meshgrid(np.arange(max(xmin, 0), min(xmax, RS)) + 0.5,
                             np.arange(max(ymin, 0), min(ymax, RS)) + 0.5)
        dd = (q[1, 1] - q[2, 1]) * (q[0, 0] - q[2, 0]) + (q[2, 0] - q[1, 0]) * (q[0, 1] - q[2, 1])
        if abs(dd) < 1e-9: continue
        w0 = ((q[1, 1] - q[2, 1]) * (xs - q[2, 0]) + (q[2, 0] - q[1, 0]) * (ys - q[2, 1])) / dd
        w1 = ((q[2, 1] - q[0, 1]) * (xs - q[2, 0]) + (q[0, 0] - q[2, 0]) * (ys - q[2, 1])) / dd
        w2 = 1 - w0 - w1
        ins = (w0 >= -1e-3) & (w1 >= -1e-3) & (w2 >= -1e-3)
        if not ins.any(): continue
        tu = (w0[..., None] * t[0] + w1[..., None] * t[1] + w2[..., None] * t[2])
        txi = np.clip(tu[..., 0], 0, 511).astype(int)
        tyi = np.clip(tu[..., 1], 0, 511).astype(int)
        col = (tex[tyi, txi] * shade[ti]).astype(np.uint8)[ins]
        yy, xx = ys[ins].astype(int), xs[ins].astype(int)
        upd = zz >= zbuf[yy, xx]
        img[yy[upd], xx[upd]] = col[upd]
        zbuf[yy[upd], xx[upd]] = zz
    return img

views = [render(0), render(45), render(80)]
gap = np.full((RS, 30, 3), 255, np.uint8)
panel = np.concatenate([views[0], gap, views[1], gap, views[2]], 1)
im = Image.fromarray(panel); dr = ImageDraw.Draw(im)
for k, (lab, col) in enumerate([('front', (255, 255, 0)), ('45deg', (0, 255, 0)), ('side', (0, 255, 255))]):
    xo = k * (RS + 30)
    dr.text((xo + RS // 2 - 40, 10), lab + ' (ea3)', fill=col)
im.save(OUT)
print('saved', OUT)
