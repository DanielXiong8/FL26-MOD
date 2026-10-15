# -*- coding: utf-8 -*-
import numpy as np, cv2, os
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

TASK = r'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'
BASE = r'D:/FL26_Mod/work/face_pipeline/track_user1'

def detect(path):
    img = cv2.imread(path)
    if img is None:
        return None
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
        running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.3)
    mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with vision.FaceLandmarker.create_from_options(opts) as l:
        r = l.detect(mpi)
    if not r.face_landmarks:
        return None
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64), (w, h)

def metrics(L):
    eyeL = (L[33] + L[133] + L[65] + L[159]) / 4
    eyeR = (L[362] + L[263] + L[385] + L[386]) / 4
    nose_tip = L[1]
    mouthL = L[61]
    mouthR = L[291]
    inter_eye = np.linalg.norm(eyeR - eyeL)
    nose_mouth = np.linalg.norm(nose_tip - L[17])
    mouth_w = np.linalg.norm(mouthR - mouthL)
    face_h = np.linalg.norm(L[152] - L[10])
    face_w = np.linalg.norm(L[234] - L[454])
    return {'inter_eye': inter_eye, 'nose_mouth': nose_mouth, 'mouth_w': mouth_w,
            'face_h': face_h, 'face_w': face_w}

targets = [('photo', 'user1_tight.jpg'),
           ('pnp_front', 'pnp_user1/render/mica_skin_front.png'),
           ('old_front', 'pnp_user1/render_old/mica_skin_front.png'),
           ('pnp_34l', 'pnp_user1/render/mica_skin_3_4_left.png')]

for tag, rel in targets:
    p = os.path.join(BASE, rel)
    d = detect(p)
    if d is None:
        print('%-12s NO FACE' % tag)
        continue
    L, wh = d
    if len(L) < 478:
        print('%-12s few lmk %d (%dx%d)' % (tag, len(L), wh[0], wh[1]))
        continue
    m = metrics(L)
    fh = m['face_h'] or 1.0
    print('%-12s img=%dx%d' % (tag, wh[0], wh[1]))
    print('   inter_eye/fh=%.3f nose_mouth/fh=%.3f mouth_w/fh=%.3f face_w/fh=%.3f' % (
        m['inter_eye'] / fh, m['nose_mouth'] / fh, m['mouth_w'] / fh, m['face_w'] / fh))
    print('   raw inter_eye=%.0f face_h=%.0f face_w=%.0f' % (m['inter_eye'], m['face_h'], m['face_w']))