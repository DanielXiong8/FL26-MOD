# -*- coding: utf-8 -*-
"""FL26 adapter - Stage 2b: TPS-based shape transfer from MICA to FL26 template.
1. Use 14 shared semantic anchors as control points.
2. Source: FL26 anchor positions (Z-up).
3. Target: MICA surface positions at same semantic locations (via kpt68 -> transform).
4. TPS to warp FL26 face vertices to MICA shape.
5. Non-face verts (top/side/back) smooth-interpolated by distance from face center.
6. Save adapted mesh + visualization.
"""
import os, json
import numpy as np
from scipy.spatial import Delaunay, KDTree
from scipy.linalg import solve

BASE = r'D:\FL26_Mod\face_benchmark'
MESH_DIR = r'D:\FL26_Mod\face_benchmark\outputs\mica\mjt1'
FL26_JSON = r'D:\FL26_Mod\work\face_pipeline\uv\mesh_se3.json'
S1 = r'D:\FL26_Mod\face_benchmark\adapter\stage1_alignment.json'
OUT = r'D:\FL26_Mod\face_benchmark\adapter\stage2_tps.json'
OUTOBJ = r'D:\FL26_Mod\face_benchmark\adapter\fl26_adapted_tps.obj'

def tps_warp(src, dst, query):
    """TPS: src (n,3) -> dst (n,3), evaluate at query (m,3). Returns (m,3)."""
    n = len(src)
    K = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            r = np.linalg.norm(src[i] - src[j])
            K[i, j] = K[j, i] = 0 if r == 0 else r**2 * np.log(r)
    P = np.c_[np.ones(n), src]  # (n, 4)
    Z = np.zeros((4, 4))
    M = np.block([[K, P], [P.T, Z]])  # (n+4, n+4)
    b = np.vstack([dst, np.zeros((4, 3))])
    coeff = solve(M, b)  # (n+4, 3)
    # evaluate
    m = len(query)
    Kq = np.zeros((m, n))
    for i in range(m):
        for j in range(n):
            r = np.linalg.norm(query[i] - src[j])
            Kq[i, j] = 0 if r == 0 else r**2 * np.log(r)
    Pq = np.c_[np.ones(m), query]
    return Kq @ coeff[:n] + Pq @ coeff[n:]

def main():
    with open(FL26_JSON) as f:
        d = json.load(f)
    fv = np.asarray(d['vertices'], np.float64)     # (700,3) Z-up
    vtri = np.asarray(d['triangles'])[:, :, 0]     # (1254,3)
    fuv = np.asarray(d['uv'], np.float64)
    # MICA
    m = __import__('trimesh').load(os.path.join(MESH_DIR, 'mesh.obj'), process=False)
    mv = np.asarray(m.vertices, np.float64)
    mf = np.asarray(m.faces, np.int64)
    mkpt = np.load(os.path.join(MESH_DIR, 'kpt68.npy'))[0]  # (68,3)
    # similarity
    with open(S1) as f:
        s1 = json.load(f)
    sim = s1['similarity']; s = sim['s']; R = np.asarray(sim['R']); t = np.asarray(sim['t'])
    mv26 = s * (mv @ R.T) + t
    # FLAME anchor points transformed to FL26 space
    fa = s1['flame_anchor3d_mm']
    shared = s1['shared']
    # Source: FL26 anchor positions
    fl = s1['fl26_anchor3d']
    # Build source & target for TPS
    src = []   # FL26 anchor positions
    tgt = []   # MICA surface positions at same semantic
    names = []
    for k in shared:
        if k not in fa:
            continue
        p_fl26 = np.asarray(fl[k])
        # target: MICA kpt at that semantic, transformed to FL26
        mp = np.asarray(fa[k])
        p_mica = s * (mp @ R.T) + t
        src.append(p_fl26)
        tgt.append(p_mica)
        names.append(k)
    src = np.array(src); tgt = np.array(tgt)
    print('TPS controls:', len(src), 'points')
    for i, k in enumerate(names):
        print(f'  {k:14s} src={np.round(src[i],4)}  tgt={np.round(tgt[i],4)}  delta={np.round(tgt[i]-src[i],4)}')

    # TPS warp of all FL26 verts
    warped = tps_warp(src, tgt, fv)
    disp = warped - fv
    print('TPS displacement: mean', np.linalg.norm(disp, axis=1).mean(), 
          'max', np.linalg.norm(disp, axis=1).max())

    # Face center for falloff: use nose_tip
    nose_fl26 = np.asarray(fl['nose_tip'])
    # Distance from nose (in FL26 units)
    dist = np.linalg.norm(fv - nose_fl26, axis=1)
    # Falloff: sigmoid at distance d0 with width w
    d0 = 0.08  # ~8cm from nose
    w = 0.03   # transition width
    alpha = 1.0 / (1.0 + np.exp((dist - d0) / w))
    # Blend: alpha*warped + (1-alpha)*original
    newv = alpha[:, None] * warped + (1 - alpha[:, None]) * fv
    print('Blend alpha: mean', alpha.mean(), 'min', alpha.min(), 'max', alpha.max())

    # Save
    result = {
        'vertices': newv.tolist(),
        'triangles': d['triangles'],
        'uv': fuv.tolist(),
        'source_mesh': 'mica_test01_front',
        'tps_controls': len(src),
        'blend': {'mean_alpha': float(alpha.mean()), 'min_alpha': float(alpha.min())},
        'displacement': {'mean': float(np.linalg.norm(disp,axis=1).mean()),
                         'max': float(np.linalg.norm(disp,axis=1).max())},
    }
    with open(OUT, 'w') as f:
        json.dump(result, f, indent=2)
    with open(OUTOBJ, 'w') as fh:
        fh.write('# FL26 adapted (MICA shape via TPS), Z-up\n')
        for v in newv:
            fh.write('v %.6f %.6f %.6f\n' % (v[0], v[1], v[2]))
        fh.write('s off\n')
        for tri in vtri:
            fh.write('f %d %d %d\n' % (tri[0]+1, tri[1]+1, tri[2]+1))
    print('saved', OUT, OUTOBJ)

if __name__ == '__main__':
    main()