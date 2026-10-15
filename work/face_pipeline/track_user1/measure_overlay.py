# -*- coding: utf-8 -*-
# measure_overlay.py - landmark deltas: overlay-composite vs current render.
# These deltas (render px) are the exact corrections the mannequin geometry needs.
import numpy as np
import cv2
from PIL import Image

BASE = r'D:\FL26_Mod\work\face_pipeline\track_user1'
blend = cv2.imread(BASE + r'\relight\overlay_direct.png')[:, 0:700]      # left tile = blend
rend = cv2.imread(BASE + r'\relight\render_full_v3\v3_front.png')
blend = cv2.resize(blend, (rend.shape[1], rend.shape[0]))

import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
TASK = 'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'

def detect(img_bgr, thr):
    h, w = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    o = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
        running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=thr)
    with vision.FaceLandmarker.create_from_options(o) as l:
        r = l.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not r.face_landmarks:
        return None
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64)

Lb = detect(blend, 0.05)
Lr = detect(rend, 0.05)
if Lb is None or Lr is None or len(Lb) < 460 or len(Lr) < 460:
    print('MP failed', len(Lb) if Lb is not None else None, len(Lr) if Lr is not None else None)
    raise SystemExit
print('[measure] blend face OK, render face OK')

# landmarks: name -> mp idx
LM = {'left_eye_c': [33, 133], 'right_eye_c': [362, 263], 'nose_tip': [1],
      'mouth_L': [61], 'mouth_R': [291], 'lip_top': [0], 'chin': [152],
      'cheek_L': [234], 'cheek_R': [454], 'brow_L': [105], 'brow_R': [334],
      'forehead': [10]}
res = {}
for n, idx in LM.items():
    pb = Lb[idx].mean(0); pr = Lr[idx].mean(0)
    res[n] = (pb, pr)
    print('%-12s blend=(%5.1f,%5.1f)  render=(%5.1f,%5.1f)  delta=(%+5.1f,%+5.1f)' % (
        n, pb[0], pb[1], pr[0], pr[1], pr[0]-pb[0], pr[1]-pb[1]))
# widths
mw_b = np.linalg.norm(res['mouth_L'][0] - res['mouth_R'][0]); mw_r = np.linalg.norm(res['mouth_L'][1] - res['mouth_R'][1])
fw_b = np.linalg.norm(res['cheek_L'][0] - res['cheek_R'][0]); fw_r = np.linalg.norm(res['cheek_L'][1] - res['cheek_R'][1])
ie_b = np.linalg.norm(res['left_eye_c'][0] - res['right_eye_c'][0]); ie_r = np.linalg.norm(res['left_eye_c'][1] - res['right_eye_c'][1])
print('mouth width: blend %.0f vs render %.0f (ratio %.2f)' % (mw_b, mw_r, mw_r/mw_b))
print('face width:  blend %.0f vs render %.0f (ratio %.2f)' % (fw_b, fw_r, fw_r/fw_b))
print('eye spacing: blend %.0f vs render %.0f (ratio %.2f)' % (ie_b, ie_r, ie_r/ie_b))
import json as _j
_dj = {}
for _n, idx in LM.items():
    _pb, _pr = res[_n]
    _dj[_n] = [float(_pb[0] - _pr[0]), float(_pb[1] - _pr[1])]   # blend - render = correction
_j.dump(_dj, open(BASE + r'\deltas.json', 'w'))
print('deltas.json:', {k: [round(v[0],1), round(v[1],1)] for k, v in _dj.items()})