# -*- coding: utf-8 -*-
# list_face_meshes.py - all meshes named face_southeuropean_new3* + prefab renderer refs
import UnityPy, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from UnityPy.export import MeshExporter
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
print('=== all Mesh objects named face_southeuropean* ===')
for o in env.objects:
    if o.type.name != 'Mesh': continue
    d = o.read(check_read=False)
    n = d.m_Name or ''
    if 'face_south' in n:
        obj = MeshExporter.export_mesh(d, 'obj')
        nv = sum(1 for l in obj.splitlines() if l.startswith('v '))
        print(n, 'verts:', nv, 'pathid:', o.path_id)
print('=== SkinnedMeshRenderer / MeshRenderer ===')
for o in env.objects:
    if o.type.name not in ('SkinnedMeshRenderer','MeshRenderer'): continue
    d = o.read(check_read=False)
    gname = ''
    try:
        go = d.m_GameObject.read()
        gname = go.m_Name
    except Exception: pass
    if 'face_southeuropean_new3' not in gname and 'face_southeuropean_new3' not in str(getattr(d,'m_Mesh','')): continue
    mesh = ''
    try: mesh = d.m_Mesh.read().m_Name
    except Exception: pass
    mats = []
    try:
        for mm in d.m_Materials:
            mats.append(mm.read().m_Name if hasattr(mm,'read') else str(mm))
    except Exception: pass
    print('GO:', gname, '| mesh:', mesh, '| materials:', mats)
