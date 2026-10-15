# -*- coding: utf-8 -*-
"""v3_shape_transfer.py — FULL MICA->game-topology shape transfer (V3).

Replaces anchor-based TPS: the person's MICA surface is sampled ONTO the game's
700-vert EA1 topology by
  1. silhouette width transfer: per-height-slice horizontal scale+center from
     the MICA silhouette (captures face/jaw WIDTH),
  2. depth-ray transfer: ray-cast along the depth axis through every (scaled)
     template vertex; the front hit on the MICA surface becomes the vertex's
     new depth (captures nose/lips/chin RELIEF exactly as MICA reconstructed it),
  3. missed rays (template verts outside the MICA silhouette, e.g. hairline)
     decay back to the template shape,
  4. Laplacian smoothing on the template adjacency.

No semantic anchors, no landmark correspondences. Everything rides on the
stage1 similarity (landmark-fit, verified: nose 4mm / lips 3mm / brow 2.6mm).

Usage: recon python v3_shape_transfer.py <run_dir>  (reads mica/mesh.obj +
adapter/stage1_alignment.json, writes adapter/stage2_ea1.json V3)
"""
import os, sys, json
import numpy as np

UV_DIR = os.path.join(os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'),
                      'work', 'face_pipeline', 'uv')


def run(run_dir, out_json=None, max_disp=0.025, z_bins=48, smooth_iters=3, lam=0.35):
    import trimesh
    from scipy.spatial import KDTree
    s1 = json.load(open(os.path.join(run_dir, 'adapter', 'stage1_alignment.json')))
    sim = s1['similarity']; s = sim['s']; R = np.asarray(sim['R']); t = np.asarray(sim['t'])
    m = trimesh.load(os.path.join(run_dir, 'mica', 'mesh.obj'), process=False)
    mfaces = np.asarray(m.faces, np.int64)
    mv = np.asarray(m.vertices, np.float64)
    mv26 = s * (mv @ R.T) + t                      # MICA in EA1 frame (meters)

    mesh = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
    tv = np.asarray(mesh['vertices'], np.float64)
    tris = np.asarray(mesh['triangles'])[:, :, 0]
    uv = np.asarray(mesh['uv'], np.float64)

    # ---- 1. silhouette width transfer (per z-slice) ----
    zmin, zmax = tv[:, 2].min(), tv[:, 2].max()
    edges = np.linspace(zmin, zmax, z_bins + 1)
    zc = (edges[:-1] + edges[1:]) / 2
    s_x = np.ones(z_bins); cx = np.zeros(z_bins)
    face_y = mv26[:, 1] < np.percentile(mv26[:, 1], 60)   # front-ish surface only
    for k in range(z_bins):
        m = (mv26[:, 2] >= edges[k]) & (mv26[:, 2] < edges[k + 1]) & face_y
        t = (tv[:, 2] >= edges[k]) & (tv[:, 2] < edges[k + 1])
        if m.sum() < 5 or t.sum() < 3:
            continue
        mm = mv26[m, 0]; tt = tv[t, 0]
        if (tt.max() - tt.min()) < 1e-6:
            continue
        s_x[k] = np.clip((mm.max() - mm.min()) / (tt.max() - tt.min()), 0.82, 1.18)
        cx[k] = (mm.max() + mm.min()) / 2 - (tt.max() + tt.min()) / 2
    # smooth profiles
    def smooth(a, it=3):
        for _ in range(it):
            a[1:-1] = (a[:-2] + 2 * a[1:-1] + a[2:]) / 4.0
        return a
    s_x = smooth(s_x); cx = smooth(cx)
    bin_idx = np.clip(((tv[:, 2] - zmin) / (zmax - zmin) * z_bins).astype(int), 0, z_bins - 1)
    x_new = tv[:, 0] + cx[bin_idx] + (tv[:, 0] - (tv[:, 0] - tv[:, 0])) * 0  # center shift first
    x_new = tv[:, 0] + cx[bin_idx]
    x_new = cx[bin_idx] + tv[:, 0] * s_x[bin_idx] + (tv.mean(0)[0] * 0)
    # note: x' = shifted center + scaled width around template's own slice center
    # (slice centers of template are ~0; cx already carries the offset)
    V2 = tv.copy(); V2[:, 0] = cx[bin_idx] + tv[:, 0] * s_x[bin_idx]

    # ---- 2. depth-ray transfer ----
    ray_mesh = trimesh.Trimesh(vertices=mv26, faces=mfaces, process=False)
    y_front = mv26[:, 1].min() - 0.05
    origins = np.stack([V2[:, 0], np.full(len(V2), y_front), V2[:, 2]], 1)
    dirs = np.tile([0.0, 1.0, 0.0], (len(V2), 1))
    hits = ray_mesh.ray.intersects_location(origins, dirs, multiple_hits=True)
    hit_pts, hit_ray = hits[0], hits[1]
    y_hit = np.full(len(V2), np.nan)
    for r in np.unique(hit_ray):
        ys = hit_pts[hit_ray == r, 1]
        y_hit[r] = ys.min()                     # FIRST hit along +y = the FRONT face surface
    # decay for missed rays via nearest valid neighbor (in x,z)
    valid = ~np.isnan(y_hit)
    if valid.sum() >= 10:
        kd = KDTree(V2[valid][:, [0, 2]])
        dd, ii = kd.query(V2[:, [0, 2]], k=1)
        conf = np.clip(1.0 - dd / 0.030, 0.0, 1.0)   # 30mm window
        y_near = np.where(valid, y_hit, V2[valid][ii][:, 1])
        # blend WITHOUT NaN propagation: missed rays keep the template depth
        y_new = V2[:, 1] * (1 - conf) + np.where(valid, y_hit, V2[:, 1]) * conf
    else:
        conf = np.zeros(len(V2)); y_new = V2[:, 1].copy()

    V3 = np.stack([x_new, y_new, tv[:, 2]], 1)
    # clamp total displacement
    disp = V3 - tv
    nrm = np.linalg.norm(disp, axis=1)
    over = nrm > max_disp
    V3[over] = tv[over] + (disp[over] * (max_disp / nrm[over])[:, None])

    # ---- 3. Laplacian smooth on template adjacency ----
    adj = {i: set() for i in range(len(tv))}
    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        adj[a].update((b, c)); adj[b].update((a, c)); adj[c].update((a, b))
    d = V3.copy()
    for _ in range(smooth_iters):
        d2 = d.copy()
        for i, nb in adj.items():
            d2[i] = (1 - lam) * d[i] + lam * d[list(nb)].mean(axis=0)
        d = d2
    V3 = d

    dn = np.linalg.norm(V3 - tv, axis=1)
    print('[v3] disp mean %.2f mm max %.2f mm | valid-depth %d/700' % (
        dn.mean() * 1000, dn.max() * 1000, int(valid.sum())))

    res = {'vertices': V3.tolist(), 'triangles': mesh['triangles'], 'uv': uv.tolist(),
           'source': 'ea1+mica_v3_depth_transfer',
           'disp_mean': float(dn.mean()), 'disp_max': float(dn.max()),
           'alpha_mean': float(conf.mean())}
    out_json = out_json or os.path.join(run_dir, 'adapter', 'stage2_ea1.json')
    with open(out_json, 'w') as f:
        json.dump(res, f, indent=2)
    print('[v3] saved', out_json)
    return out_json


if __name__ == '__main__':
    run(sys.argv[1])
