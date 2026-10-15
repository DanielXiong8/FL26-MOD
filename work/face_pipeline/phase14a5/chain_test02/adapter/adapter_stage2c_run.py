# -*- coding: utf-8 -*-
"""FL26 adapter - Stage 2c: TPS on EASTASIA template (better shape match).
Use ea1 (eastasia_new1) as base template instead of se3 (southeuropean_new3).
Then apply MICA identity shape via TPS with 14 semantic anchors.
Landmarks from uv_landmark_map.json (shared topology).
"""
import os, json
import numpy as np
from scipy.spatial import KDTree, Delaunay
from scipy.linalg import solve

BASE = r'C:\FL26_Mod\face_benchmark'
MESH_DIR = 'D:\\FL26_Mod\\work\\face_pipeline\\phase14a5\\chain_test02\\mica'
EA1 = r'C:\FL26_Mod\work\face_pipeline\uv\mesh_ea1.json'
UV_LM = r'C:\FL26_Mod\work\face_pipeline\uv\uv_landmark_map.json'
S1 = 'D:\\FL26_Mod\\work\\face_pipeline\\phase14a5\\chain_test02\\adapter\\stage1_alignment.json'
OUTOBJ = r'C:\FL26_Mod\face_benchmark\adapter\fl26_ea1_adapted.obj'
OUTJSON = 'D:\\FL26_Mod\\work\\face_pipeline\\phase14a5\\chain_test02\\adapter\\stage2_ea1.json'
def tps_warp(src, dst, query):
    n = len(src)
    K = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            r = np.linalg.norm(src[i] - src[j])
            K[i, j] = K[j, i] = 0 if r == 0 else r**2 * np.log(r + 1e-10)
    P = np.c_[np.ones(n), src]
    Z = np.zeros((4, 4))
    M = np.block([[K, P], [P.T, Z]])
    b = np.vstack([dst, np.zeros((4, 3))])
    coeff = solve(M, b)
    m = len(query)
    Kq = np.zeros((m, n))
    for i in range(m):
        for j in range(n):
            r = np.linalg.norm(query[i] - src[j])
            Kq[i, j] = 0 if r == 0 else r**2 * np.log(r + 1e-10)
    Pq = np.c_[np.ones(m), query]
    return Kq @ coeff[:n] + Pq @ coeff[n:]

def main():
    with open(EA1) as f:
        d = json.load(f)
    fv = np.asarray(d['vertices'], np.float64)  # ea1 (700,3)
    vtri = np.asarray(d['triangles'])[:, :, 0]
    fuv = np.asarray(d['uv'], np.float64)
    # MICA
    m = __import__('trimesh').load(os.path.join(MESH_DIR, 'mesh.obj'), process=False)
    mv = np.asarray(m.vertices, np.float64)
    mkpt = np.load(os.path.join(MESH_DIR, 'kpt68.npy'))[0]
    with open(S1) as f:
        s1 = json.load(f)
    sim = s1['similarity']; s = sim['s']; R = np.asarray(sim['R']); t = np.asarray(sim['t'])
    mv26 = s * (mv @ R.T) + t
    # MICA keypoints in FL26 space
    fa = s1['flame_anchor3d_mm']
    shared = s1['shared']
    # FL26 (ea1) anchor positions: read from uv_landmark_map (same topology, same v_idx)
    with open(UV_LM) as f:
        lm = json.load(f)['landmarks']
    # Source: ea1 anchor points (from uvl landmark 3d)
    src = []
    tgt = []
    for k in shared:
        if k not in fa: continue
        p_ea1 = np.asarray(lm[k]['3d'])
        mp = np.asarray(fa[k])
        p_mica = s * (mp @ R.T) + t
        src.append(p_ea1)
        tgt.append(p_mica)
    src = np.array(src); tgt = np.array(tgt)
    print('Controls:', len(src))
    for i, k in enumerate(shared):
        print(f'  {k:14s} delta={np.round(tgt[i]-src[i],4)}')

    # TPS warp all ea1 verts
    warped = tps_warp(src, tgt, fv)
    disp = np.linalg.norm(warped - fv, axis=1)
    print('TPS disp mean', disp.mean(), 'max', disp.max())

    # Blend: falloff from nose_tip
    nose = np.asarray(lm['nose_tip']['3d'])
    d_nose = np.linalg.norm(fv - nose, axis=1)
    d0, w = 0.08, 0.03
    alpha = 1.0 / (1.0 + np.exp((d_nose - d0) / w))
    newv = alpha[:, None] * warped + (1 - alpha[:, None]) * fv
    print('Alpha mean', alpha.mean(), 'min', alpha.min())

    # Save
    res = {
        'vertices': newv.tolist(), 'triangles': d['triangles'], 'uv': fuv.tolist(),
        'source': 'ea1+mica_test01_front_tps',
        'disp_mean': float(disp.mean()), 'disp_max': float(disp.max()),
        'alpha_mean': float(alpha.mean()),
    }
    with open(OUTJSON, 'w') as f:
        json.dump(res, f, indent=2)
    with open(OUTOBJ, 'w') as fh:
        fh.write('# FL26 EastAsia adapted (MICA shape), Z-up\n')
        for v in newv: fh.write('v %.6f %.6f %.6f\n' % (v[0], v[1], v[2]))
        fh.write('s off\n')
        for tri in vtri: fh.write('f %d %d %d\n' % (tri[0]+1, tri[1]+1, tri[2]+1))
    print('saved', OUTOBJ, OUTJSON)

if __name__ == '__main__':
    main()