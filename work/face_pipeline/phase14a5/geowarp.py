# -*- coding: utf-8 -*-
"""geowarp.py — MICA-driven geometry warp of the EA1 700-vert face template.

Unlike stage2c (TPS through semantic landmark anchors, which carries cm-scale
mapping bias), this derives per-vertex displacement directly from GEOMETRY:

  1. load stage1 similarity (FLAME mm,Y-up -> FL26 m,Z-up) and the MICA mesh
  2. transform MICA verts into FL26 space
  3. for every EA1 template vertex: nearest-point displacement toward the MICA
     surface (KDTree), confidence-weighted by NN distance, magnitude-clamped
  4. Laplacian-smooth the displacement field on the template mesh adjacency

UVs are untouched, so the photo bake (painted on EA1 UVs) follows the warped
surface coherently. Output overwrites adapter/stage2_ea1.json in the run dir.
"""
import json, os, sys
import numpy as np


def run(run_dir, max_disp=0.006, nn_conf=0.009, smooth_iters=2, lam=0.5):
    s1 = json.load(open(os.path.join(run_dir, 'adapter', 'stage1_alignment.json')))
    sim = s1['similarity']; s = sim['s']; R = np.asarray(sim['R']); t = np.asarray(sim['t'])
    import trimesh
    m = trimesh.load(os.path.join(run_dir, 'mica', 'mesh.obj'), process=False)
    mv = np.asarray(m.vertices, np.float64)
    mv26 = s * (mv @ R.T) + t

    from scipy.spatial import KDTree
    tv = np.asarray(json.load(open(os.path.join(
        os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'),
        'work', 'face_pipeline', 'uv', 'mesh_ea1.json')))['vertices'], np.float64)
    tris = np.asarray(json.load(open(os.path.join(
        os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'),
        'work', 'face_pipeline', 'uv', 'mesh_ea1.json')))['triangles'])[:, :, 0]

    tree_mica = KDTree(mv26)
    # NO ICP: stage1 similarity is landmark-fit and puts the central face axis
    # within ~3-5mm (verified: nose 4.4mm, lips 3.3mm, brow 2.6mm). Full-cloud
    # ICP/Umeyama made alignment WORSE (skull vs face-patch mismatch). Trust the
    # landmark fit and let the confidence mask handle the periphery.
    nn_d, nn_i = tree_mica.query(tv, k=1)
    disp = mv26[nn_i] - tv
    # confidence: fade out where the template has no nearby MICA surface
    conf = np.clip(1.0 - nn_d / nn_conf, 0.0, 1.0)
    disp *= conf[:, None]
    # clamp magnitude
    nrm = np.linalg.norm(disp, axis=1)
    over = nrm > max_disp
    disp[over] *= (max_disp / nrm[over])[:, None]

    # Laplacian smoothing over template adjacency
    adj = {}
    for tri in tris:
        for a in tri:
            adj.setdefault(int(a), set())
    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        adj[a].update((b, c)); adj[b].update((a, c)); adj[c].update((a, b))
    d = disp.copy()
    for _ in range(smooth_iters):
        d2 = d.copy()
        for i, nb in adj.items():
            d2[i] = (1 - lam) * d[i] + lam * d[list(nb)].mean(axis=0)
        d = d2

    newv = tv + d
    disp_stats = np.linalg.norm(d, axis=1)
    print('geowarp: disp mean %.4f mm max %.4f mm | zeroed(no-conf) %d/700' % (
        disp_stats.mean() * 1000, disp_stats.max() * 1000, int((conf == 0).sum())))

    uv = np.asarray(json.load(open(os.path.join(
        os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'),
        'work', 'face_pipeline', 'uv', 'mesh_ea1.json')))['uv'], np.float64)
    res = {'vertices': newv.tolist(), 'triangles': tris.tolist(), 'uv': uv.tolist(),
           'source': 'ea1+mica_geowarp',
           'disp_mean': float(disp_stats.mean()), 'disp_max': float(disp_stats.max()),
           'alpha_mean': float(conf.mean())}
    out = os.path.join(run_dir, 'adapter', 'stage2_ea1.json')
    with open(out, 'w') as f:
        json.dump(res, f, indent=2)
    print('saved', out)
    return out


if __name__ == '__main__':
    run(sys.argv[1])
