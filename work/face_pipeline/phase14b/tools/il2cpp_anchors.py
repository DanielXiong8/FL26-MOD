# -*- coding: utf-8 -*-
"""il2cpp_anchors.py — Phase14B §5: static string-anchor analysis.
Searches global-metadata.dat (all C# string literals) for the appearance
pipeline's class/method names, and libil2cpp.so for the corresponding
token-referenced strings. Output: il2cpp_anchors.json
"""
import json, re, os

META = r'D:\FL26_Mod\work\face_pipeline\phase14b\il2cpp\global-metadata.dat'
SO = r'D:\FL26_Mod\work\face_pipeline\phase14b\il2cpp\libil2cpp.so'
OUT = r'D:\FL26_Mod\work\face_pipeline\phase14b\il2cpp_anchors.json'

terms = ['FaceTemplate', 'FaceMaterialSupplier', 'PlayerAppearance', 'FaceConfig',
         'FaceBlend', 'SetVertices', 'GetVertices', 'bindposes', 'BoneWeight',
         'face_eastAsia_new', 'face_EastAsia_new', 'FaceShape', 'FaceIcon',
         'PlayerFace', 'FaceSettings', 'faceTextureId', 'faceTemplateId',
         'PlayerAppearanceTable', 'AppearanceTable']

meta = open(META, 'rb').read()
so = open(SO, 'rb').read()
res = {'metadata_size': len(meta), 'so_size': len(so), 'hits': {}}
for t in terms:
    tb = t.encode('utf-8')
    offs = [m.start() for m in re.finditer(re.escape(tb), meta)]
    if offs:
        # context: neighboring strings (null-delimited window)
        ctx = []
        for o in offs[:3]:
            s0 = meta.rfind(0, max(0, o - 200), o)
            ctx.append(meta[s0 + 1:o + len(tb) + 60].decode('utf-8', errors='replace'))
        res['hits'][t] = {'count_meta': len(offs), 'first_off': offs[0], 'ctx': ctx}
    so_offs = [m.start() for m in re.finditer(re.escape(tb), so)]
    if so_offs:
        res['hits'].setdefault(t, {})['count_so'] = len(so_offs)
        res['hits'][t]['so_first_off'] = so_offs[0]

json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
for t in terms:
    h = res['hits'].get(t)
    if h:
        print('%-24s meta=%-4s so=%-4s' % (t, h.get('count_meta', 0), h.get('count_so', 0)))
print('saved', OUT)
