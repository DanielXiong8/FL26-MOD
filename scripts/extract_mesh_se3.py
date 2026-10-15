# -*- coding: utf-8 -*-
# extract_mesh_se3.py v2 - export face_southeuropean_new3 via OBJ exporter
import json
import numpy as np
import UnityPy
from UnityPy.export import MeshExporter

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
for o in env.objects:
    if o.type.name != 'Mesh':
        continue
    d = o.read(check_read=False)
    if (d.m_Name or '') == 'face_southeuropean_new3':
        obj = MeshExporter.export_mesh(d, 'obj')
        vs, vts, fs = [], [], []
        for line in obj.splitlines():
            p = line.split()
            if not p:
                continue
            if p[0] == 'v':
                vs.append([float(x) for x in p[1:4]])
            elif p[0] == 'vt':
                vts.append([float(x) for x in p[1:3]])
            elif p[0] == 'f':
                tri = []
                for tok in p[1:4]:
                    parts = tok.split('/')
                    vi = int(parts[0]) - 1
                    ti = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else vi
                    tri.append((vi, ti))
                fs.append(tri)
        V = np.array(vs, np.float32)
        U = np.array(vts, np.float32)
        print('verts', V.shape, 'uvs', U.shape, 'tris', len(fs))
        print('v range x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f' % (V[:,0].min(),V[:,0].max(),V[:,1].min(),V[:,1].max(),V[:,2].min(),V[:,2].max()))
        print('uv range u %.3f..%.3f v %.3f..%.3f' % (U[:,0].min(),U[:,0].max(),U[:,1].min(),U[:,1].max()))
        # vertex->uv map (assumed 1:1 export order from exporter)
        # build vertex-indexed uv via first triangle occurrence
        v2t = {}
        for tri in fs:
            for vi, ti in tri:
                v2t.setdefault(vi, ti)
        Uv = np.zeros((len(V), 2), np.float32)
        ok = np.zeros(len(V), bool)
        for vi, ti in v2t.items():
            Uv[vi] = U[ti]; ok[vi] = True
        print('verts with uv:', int(ok.sum()), '/', len(V))
        out = dict(mesh='face_southeuropean_new3',
                   vertices=V.tolist(),
                   uv=Uv.tolist(),
                   uv_ok=ok.tolist(),
                   triangles=[[[vi, ti] for vi, ti in tri] for tri in fs])
        json.dump(out, open(r'C:\FL26_Mod\work\face_pipeline\uv\mesh_se3.json', 'w'))
        print('saved -> mesh_se3.json')
        break
