# -*- coding: utf-8 -*-
# uv_fix1.py - parse the GAME mesh asset's UVs, verify against mesh_ea1, and
# diagnose the eye-band overlapping vertex clusters (eye-front vs eyelid).
import os, json, zipfile
import numpy as np
import UnityPy

ROOT = r'D:\FL26_Mod'
BASE_APK = os.path.join(ROOT, 'build', 'base_debuggable2.apk')
EA1 = json.load(open(os.path.join(ROOT, 'work', 'face_pipeline', 'uv', 'mesh_ea1.json')))
V = np.array(EA1['vertices'], np.float64)
UV = np.array(EA1['uv'], np.float64)

with zipfile.ZipFile(BASE_APK) as z:
    open('avatar_probe.unity3d', 'wb').write(z.read('assets/bundles/avatar.unity3d'))
env = UnityPy.load('avatar_probe.unity3d')
for obj in env.objects:
    if obj.type.name != 'Mesh':
        continue
    m = obj.read()
    if m.m_Name != 'face_EastAsia_new1':
        continue
    tree = obj.read_typetree()
    vd = tree['m_VertexData']
    nvert = vd['m_VertexCount']
    chans = vd['m_Channels']
    print('nvert', nvert, 'm_DataSize', len(vd['m_DataSize']))
    for c in chans:
        print('  ch stream=%d offset=%d dim=%d' % (c['stream'], c['offset'], c['dimension']))
    # stream strides
    strides = {}
    for c in chans:
        if c['dimension'] == 0:
            continue
        strides.setdefault(c['stream'], 0)
        strides[c['stream']] = max(strides[c['stream']], c['offset'] + c['dimension'] * 4)
    print('stream strides:', strides)
    data = bytes(vd['m_DataSize'])
    # stream0 = pos+normal+... packed first; stream1 base = nvert * stride0
    s0 = strides.get(0, 0)
    base1 = nvert * s0
    cuv = [c for c in chans if c['stream'] == 1 and c['dimension'] == 2][0]
    fl = np.frombuffer(data, np.float32)
    uv_all = fl[base1 // 4:].reshape(-1, strides[1] // 4)[:, cuv['offset'] // 4:cuv['offset'] // 4 + 2]
    print('parsed uv_all shape', uv_all.shape)
    ga = uv_all[:nvert]
    # compare with mesh_ea1 uv (ea1 convention: u as-is, v flipped?)
    for tag, conv in [('as-is', np.array([1.0, 1.0])), ('v-flip', np.array([1.0, -1.0]))]:
        d = np.abs(ga - UV * conv).max()
        print('  vs mesh_ea1 uv (%s): max diff %.5f' % (tag, d))
    np.save('uv_asset_new1.npy', ga)
    break
