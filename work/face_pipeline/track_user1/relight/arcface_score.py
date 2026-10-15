# -*- coding: utf-8 -*-
# arcface_score.py - objective likeness: cos(embedding(photo), embedding(render)).
# Run with the recon env python (has insightface antelopev2).
import sys, os
import numpy as np
import cv2

sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from insightface.app import FaceAnalysis
from insightface.utils.face_align import norm_crop

app = FaceAnalysis(name='antelopev2', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(224, 224), det_thresh=0.3)

def embed(path):
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        img = cv2.imread(path)
    assert img is not None, path
    faces = app.get(img)
    if not faces:
        return None
    f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    aimg = norm_crop(img, landmark=f.kps, image_size=112)
    e = app.models['recognition'].get_feat([aimg])[0]
    return e / (np.linalg.norm(e) + 1e-9)

BASE = r'D:\FL26_Mod\work\face_pipeline\track_user1'
targets = [
    ('photo', os.path.join(BASE, 'user1_tight.jpg')),
    ('old_golden_render', os.path.join(BASE, 'relight', 'render_old', 'v2_front.png')),
    ('relit_render', os.path.join(BASE, 'relight', 'render_new', 'v2_front.png')),
]
embs = {}
for tag, p in targets:
    e = embed(p)
    embs[tag] = e
    print('%-18s %s' % (tag, 'NO FACE' if e is None else 'emb ok'))

if embs.get('photo') is not None:
    pe = embs['photo']
    for tag in ('old_golden_render', 'relit_render'):
        if embs.get(tag) is not None:
            c = float(np.dot(pe, embs[tag]))
            print('cos(photo, %-18s) = %.4f' % (tag, c))
