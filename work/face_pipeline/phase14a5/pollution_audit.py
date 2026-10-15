# -*- coding: utf-8 -*-
import zipfile, io
import numpy as np
import UnityPy

def dump_ea(apk):
    z = zipfile.ZipFile(apk)
    env = UnityPy.load(io.BytesIO(z.read('assets/bundles/avatar.unity3d')))
    out = {'mesh': {}, 'tex': {}}
    for obj in env.objects:
        if obj.type.name == 'Mesh':
            d = obj.read()
            if d.m_Name.startswith('face_EastAsia_new'):
                tree = obj.read_typetree()
                vd = tree['m_VertexData']
                ch0 = vd['m_Channels'][0]
                stride = max(c['offset'] + c['dimension'] * 4 for c in vd['m_Channels'] if c['stream'] == 0)
                fl = np.frombuffer(bytes(vd['m_DataSize']), np.float32)
                nvert = vd['m_VertexCount']
                stride_f = len(fl) // max(nvert, 1)
                off = ch0['offset'] // 4
                pos = fl.reshape(nvert, stride_f)[:, off:off + 3].astype(np.float64)
                out['mesh'][d.m_Name] = (nvert, pos)
        if obj.type.name == 'Texture2D':
            d = obj.read()
            if d.m_Name.startswith('face_eastAsia_new'):
                try:
                    out['tex'][d.m_Name] = np.asarray(d.image.convert('RGB'), np.int16)
                except Exception as e:
                    pass
    return out

A = dump_ea(r'C:\Users\Lenovo\OneDrive\Desktop\fl26mod\原安装包\base.apk')
B = dump_ea(r'D:\FL26_Mod\build\base_debuggable2.apk')
for i in range(1, 7):
    nm = 'face_EastAsia_new%d' % i
    ma, mb = A['mesh'].get(nm), B['mesh'].get(nm)
    if ma and mb:
        if ma[0] == mb[0] and ma[1].shape == mb[1].shape:
            print('%s mesh: verts %d | diff max %.6f' % (nm, ma[0], np.abs(ma[1] - mb[1]).max()))
        else:
            print('%s mesh: verts %d vs %d (DIFFERENT)' % (nm, ma[0], mb[0]))
    else:
        print('%s mesh: A=%s B=%s' % (nm, bool(ma), bool(mb)))
for i in range(1, 7):
    nm = 'face_eastAsia_new%d' % i
    ta, tb = A['tex'].get(nm), B['tex'].get(nm)
    if ta is not None and tb is not None and ta.shape == tb.shape:
        print('%s tex: mean diff %.3f' % (nm, np.abs(ta - tb).mean()))
    else:
        print('%s tex: A=%s B=%s' % (nm, ta is not None, tb is not None))
