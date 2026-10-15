# -*- coding: utf-8 -*-
"""FL26 adapter - Stage 1: coordinate align + semantic landmark mapping.
Builds correspondence between FL26 template (19 semantic anchors, Z-up) and
MICA FLAME mesh (68 kpt, mm, Y-up), then estimates a coarse similarity transform.
Outputs a JSON with the mapping + transform + sanity metrics.
"""
import os, json
import numpy as np

BASE = r'C:\FL26_Mod\face_benchmark'
MESH_DIR = 'D:\\FL26_Mod\\work\\face_pipeline\\regression\\set3_oip_chain\\mica'
FL26_JSON = r'C:\FL26_Mod\work\face_pipeline\uv\mesh_se3.json'
UV_LM = r'C:\FL26_Mod\work\face_pipeline\uv\uv_landmark_map.json'
OUT = 'D:\\FL26_Mod\\work\\face_pipeline\\regression\\set3_oip_chain\\adapter\\stage1_alignment.json'

# FLAME ibug68 semantic -> FL26 anchor. Value = list of kpt indices to average (or single).
# For anchors not directly in ibug68, we compute from mesh geometry in stage2.
KPT_MAP = {
    'brow_center':  [19, 24],      # left brow + right brow midpoint
    'left_eye':     list(range(36, 42)),
    'right_eye':    list(range(42, 48)),
    'nose_bridge':  [27, 28],
    'nose_tip':     [30],
    'nose_base':    list(range(31, 36)),
    'lip_upper':    [51],
    'lip_lower':    [57],
    'mouth_left':   [48],
    'mouth_right':  [54],
    'chin':         [8],
    'chin_bottom':  [7],
    'jaw_left':     [4, 5],
    'jaw_right':    [11, 12],
}

def load_fl26():
    with open(FL26_JSON) as f:
        d = json.load(f)
    verts = np.asarray(d['vertices'], np.float64)      # (700,3)
    tris = np.asarray(d['triangles'], np.int64)         # (1254,3,2)
    uv = np.asarray(d['uv'], np.float64)
    # triangles[:, :, 0] = vertex indices, [:, :, 1] = uv indices
    vtri = tris[:, :, 0]
    return verts, vtri, uv

def load_mica():
    import trimesh
    m = trimesh.load(os.path.join(MESH_DIR, 'mesh.obj'), process=False)
    verts = np.asarray(m.vertices, np.float64)          # (5023,3) mm, FLAME canonical Y-up
    kpt = np.load(os.path.join(MESH_DIR, 'kpt68.npy'))[0]  # (68,3)
    return verts, kpt

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fv, ftri, fuv = load_fl26()
    mv, mkpt = load_mica()
    print('FL26:', fv.shape, 'tri', ftri.shape)
    print('MICA:', mv.shape, 'kpt', mkpt.shape)
    print('MICA kpt z range', mkpt[:,2].min(), mkpt[:,2].max())

    # Build FLAME kpt anchors (mm)
    anchor_pts = {}   # name -> 3D (FLAME coords, mm)
    for name, idxs in KPT_MAP.items():
        anchor_pts[name] = mkpt[idxs].mean(axis=0)
    print('\nFLAME anchor pts (mm):')
    for k, v in anchor_pts.items():
        print(f'  {k:14s}', np.round(v, 1))

    # FL26 anchors 3D (Z-up shell units)
    with open(UV_LM) as f:
        lm = json.load(f)['landmarks']
    fl26_pts = {k: np.asarray(v['3d'], np.float64) for k, v in lm.items()}
    print('\nFL26 anchor pts (Z-up):')
    for k, v in fl26_pts.items():
        print(f'  {k:14s}', np.round(v, 4))

    # Shared semantic anchors (present in both)
    shared = [k for k in anchor_pts if k in fl26_pts]
    print('\nshared anchors:', shared)

    # For rigid alignment use only central rigid region (eyes/nose/mouth/brow)
    # Contour anchors (jaw/chin_bottom) have semantic offset between FLAME & FL26
    RIGID_CORE = ['brow_center', 'left_eye', 'right_eye', 'nose_bridge',
                  'nose_tip', 'nose_base', 'lip_upper', 'lip_lower',
                  'mouth_left', 'mouth_right']
    rigid_shared = [k for k in RIGID_CORE if k in shared]
    print('rigid-core anchors:', rigid_shared)

    # Estimate similarity transform FLAME(mm, Y-up) -> FL26(Z-up)
    # Use umeyama on shared points.
    A = np.stack([anchor_pts[k] for k in rigid_shared])   # (n,3) FLAME
    B = np.stack([fl26_pts[k] for k in rigid_shared])     # (n,3) FL26
    def umeyama(src, dst):
        n = src.shape[0]
        mu_s = src.mean(0); mu_d = dst.mean(0)
        sc = src - mu_s; dc = dst - mu_d
        cov = dc.T @ sc / n
        U, S, Vt = np.linalg.svd(cov)
        d = np.ones(3); d[-1] = np.sign(np.linalg.det(U @ Vt))
        R = U @ np.diag(d) @ Vt
        var = (sc**2).sum() / n
        s = S.sum() / var
        t = mu_d - s * R @ mu_s
        return s, R, t
    s, R, t = umeyama(A, B)
    print('\nSimilarity transform FLAME->FL26:')
    print('  s =', s)
    print('  R =\n', np.round(R, 3))
    print('  t =', np.round(t, 4))

    # Verify: transform FLAME anchors into FL26 space, measure residual
    A_t = s * (A @ R.T) + t
    err = np.linalg.norm(A_t - B, axis=1)
    print('\nResidual (FL26 units) per rigid anchor:')
    for i, k in enumerate(rigid_shared):
        print(f'  {k:14s} {err[i]:.4f}')
    print('  mean residual:', err.mean())
    # also report all-shared residual for info
    Aa = np.stack([anchor_pts[k] for k in shared])
    Bb = np.stack([fl26_pts[k] for k in shared])
    err_all = np.linalg.norm(s * (Aa @ R.T) + t - Bb, axis=1)
    print('  all-shared mean residual (info):', err_all.mean())

    # Save
    result = {
        'fl26_anchor3d': {k: fl26_pts[k].tolist() for k in fl26_pts},
        'flame_anchor3d_mm': {k: anchor_pts[k].tolist() for k in anchor_pts},
        'kpt_map': KPT_MAP,
        'shared': shared,
        'rigid_core': rigid_shared,
        'similarity': {'s': float(s), 'R': R.tolist(), 't': t.tolist()},
        'residual_mean': float(err.mean()),
        'residual_all_shared': float(err_all.mean()),
        'fl26_coord': 'Z-up shell', 'flame_coord': 'Y-up mm',
    }
    with open(OUT, 'w') as f:
        json.dump(result, f, indent=2)
    print('\nsaved', OUT)

if __name__ == '__main__':
    main()
