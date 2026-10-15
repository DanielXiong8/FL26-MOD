# -*- coding: utf-8 -*-
"""probe_mesh_slots.py — determine which face_EastAsia_newK MESH each b1 renders.

Transforms each slot's OWN mesh vertices in place (no topology change):
  new1 = stock      new2 = tall(y1.35)   new3 = flat(y0.7)
  new4 = wide(x1.4) new5 = narrow(x0.6)  new6 = big(all1.2)
Then the B-probe players (b1=10..15) render; the user reads each head shape
-> mesh-slot mapping locked (or disproven if all identical).
"""
import sys, os, zipfile, shutil
import numpy as np
sys.path.insert(0, r'D:\FL26_Mod\tools\FL26_FaceBuilderWeb\backend')
import UnityPy

APK = sys.argv[1]
av_dir = os.path.join(os.path.dirname(APK), 'avatar_work')
os.makedirs(av_dir, exist_ok=True)
av_src = os.path.join(av_dir, 'avatar_probe.unity3d')
with zipfile.ZipFile(APK) as z:
    open(av_src, 'wb').write(z.read('assets/bundles/avatar.unity3d'))
shutil.copyfile(av_src, av_src + '.mod')
env = UnityPy.load(av_src + '.mod')

TF = {1: ('stock', np.array([1.0, 1.0, 1.0])),
      2: ('tall', np.array([1.0, 1.35, 1.0])),
      3: ('flat', np.array([1.0, 0.70, 1.0])),
      4: ('wide', np.array([1.40, 1.0, 1.0])),
      5: ('narrow', np.array([0.60, 1.0, 1.0])),
      6: ('big', np.array([1.20, 1.20, 1.20]))}

done = set()
for obj in env.objects:
    if obj.type.name != 'Mesh':
        continue
    d = obj.read()
    nm = d.m_Name
    if not nm.startswith('face_EastAsia_new'):
        continue
    try:
        k = int(nm.rsplit('new', 1)[1])
    except ValueError:
        continue
    tag, scale = TF[k]
    tree = obj.read_typetree()
    vd = tree['m_VertexData']
    nvert = vd['m_VertexCount']
    fl = np.frombuffer(bytes(vd['m_DataSize']), np.float32)
    stride_f = len(fl) // max(nvert, 1)
    center = fl.reshape(nvert, stride_f)[:, 0:3].mean(axis=0)
    arr = fl.reshape(nvert, stride_f).copy()
    arr[:, 0] = center[0] + (arr[:, 0] - center[0]) * scale[0]
    arr[:, 1] = center[1] + (arr[:, 1] - center[1]) * scale[1]
    arr[:, 2] = center[2] + (arr[:, 2] - center[2]) * scale[2]
    vd['m_DataSize'] = arr.tobytes()
    tree['m_VertexData'] = vd
    obj.save_typetree(tree)
    done.add(k)
    print('mesh %s <- %s transform (%d verts)' % (nm, tag, nvert))
assert len(done) == 6, done

with open(av_src + '.mod', 'wb') as f:
    f.write(env.file.save())
tmp = APK + '.t'
with zipfile.ZipFile(APK, 'r') as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        zout.writestr(item, open(av_src + '.mod', 'rb').read() if item.filename == 'assets/bundles/avatar.unity3d' else zin.read(item.filename))
shutil.move(tmp, APK)
print('probe meshes injected OK')
