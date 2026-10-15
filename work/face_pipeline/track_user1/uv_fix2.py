# -*- coding: utf-8 -*-
# uv_fix2.py - diagnose eye-band vertex clusters (eye-front vs eyelid) and write
# corrected UVs (lid cluster moved up out of the eye band) into stage2_final.json.
import os, json
import numpy as np

WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
EA1 = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(EA1['vertices'], np.float64)
UV = np.array(EA1['uv'], np.float64)          # asset convention as-is
TEX = 1024

# eye band in mesh-uv: texture rows ty 262..366 -> v = 1 - ty/TEX
v_lo, v_hi = 1 - 366.0 / TEX, 1 - 262.0 / TEX
bands = [('L', 350.0 / TEX, 480.0 / TEX), ('R', 596.0 / TEX, 726.0 / TEX)]
mask = np.zeros(len(V), bool)
for side, u_lo, u_hi in bands:
    mask |= (UV[:, 0] >= u_lo) & (UV[:, 0] <= u_hi) & (UV[:, 1] >= v_lo) & (UV[:, 1] <= v_hi)
idx = np.where(mask)[0]
print('verts with UV in eye band: %d' % len(idx))
# 3D clusters by y (front) — print sorted by y
order = idx[np.argsort(V[idx, 1])]
for i in order:
    print('  v%3d uv=(%.3f,%.3f) V=(%+.4f,%+.4f,%+.4f)' % (i, UV[i,0], UV[i,1], V[i,0], V[i,1], V[i,2]))
