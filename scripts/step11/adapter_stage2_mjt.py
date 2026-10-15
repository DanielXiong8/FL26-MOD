# -*- coding: utf-8 -*-
"""FL26 adapter - Stage 2: map FL26 template verts onto MICA mesh surface.
Steps:
1. Load stage1 similarity transform (FLAME mm Y-up -> FL26 Z-up).
2. Transform MICA mesh (FLAME mm) into FL26 coordinate space.
3. For each FL26 vertex, find closest point on MICA mesh surface (point-triangle).
4. Move FL26 vertex to that surface point -> FL26 topology, MICA shape.
5. Save new FL26 mesh (obj + json) + sanity metrics.
"""
import os, json
import numpy as np
import trimesh

BASE = r'D:\FL26_Mod\face_benchmark'
MESH_DIR = r'D:\FL26_Mod\face_benchmark\outputs\mica\mjt1'
FL26_JSON = r'D:\FL26_Mod\work\face_pipeline\uv\mesh_se3.json'
S1 = r'D:\FL26_Mod\face_benchmark\adapter\stage1_alignment.json'
OUT = os.path.join(BASE, 'adapter', 'stage2_adapted.json')
OUTOBJ = os.path.join(BASE, 'adapter', 'fl26_adapted.obj')

def main():
    # load FL26 template
    with open(FL26_JSON) as f:
        d = json.load(f)
    fv = np.asarray(d['vertices'], np.float64)     # (700,3) Z-up
    ftri = np.asarray(d['triangles'], np.int64)    # (1254,3,2)
    vtri = ftri[:, :, 0]
    fuv = np.asarray(d['uv'], np.float64)
    # load MICA mesh (FLAME mm Y-up)
    m = trimesh.load(os.path.join(MESH_DIR, 'mesh.obj'), process=False)
    mv = np.asarray(m.vertices, np.float64)
    mf = np.asarray(m.faces, np.int64)
    # load similarity transform
    with open(S1) as f:
        s1 = json.load(f)
    sim = s1['similarity']
    s = sim['s']; R = np.asarray(sim['R']); t = np.asarray(sim['t'])

    # Transform MICA verts into FL26 space: p' = s*(p@R.T)+t
    mv26 = s * (mv @ R.T) + t
    print('MICA in FL26 space:', mv26.shape)

    # Build trimesh of MICA in FL26 space for closest-point queries
    mica = trimesh.Trimesh(vertices=mv26, faces=mf, process=False)
    print('MICA faces:', len(mf))

    # For each FL26 vertex, find closest point on MICA surface
    pts = np.asarray(fv, np.float64)
    closest, dist, tid = trimesh.proximity.closest_point(mica, pts)
    print('closest_point done. dist mean/std/max:',
          dist.mean(), dist.std(), dist.max())

    # new FL26 verts = closest surface points (MICA shape)
    newv = closest
    # Keep topology + uv unchanged
    result = {
        'vertices': newv.tolist(),
        'triangles': d['triangles'],
        'uv': fuv.tolist(),
        'source_mesh': 'mica_test01_front',
        'align': s1,
        'dist': {'mean': float(dist.mean()), 'std': float(dist.std()),
                 'max': float(dist.max())},
        'num_verts': len(newv), 'num_tris': len(vtri),
    }
    with open(OUT, 'w') as f:
        json.dump(result, f, indent=2)
    # export obj (with uv + vn placeholder)
    with open(OUTOBJ, 'w') as fh:
        fh.write('# FL26 adapted (MICA shape), Z-up\n')
        for v in newv:
            fh.write('v %.6f %.6f %.6f\n' % (v[0], v[1], v[2]))
        fh.write('s off\n')
        for tri in vtri:
            fh.write('f %d %d %d\n' % (tri[0]+1, tri[1]+1, tri[2]+1))
    print('saved', OUT, 'and', OUTOBJ)
    print('dist summary in FL26 units (1 unit~1m):')
    print('  mean', dist.mean(), 'm; max', dist.max(), 'm; mean mm', dist.mean()*1000)

if __name__ == '__main__':
    main()
