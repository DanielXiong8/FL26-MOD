# -*- coding: utf-8 -*-
# overlay1.py - direct 2D overlay of the reference photo's face onto the render,
# aligned by the eyes. Outputs: ghost blend (shows displacement) + opaque paste
# (the "photo directly overlaid on the head" look).
import numpy as np
import cv2
from PIL import Image

BASE = r'D:\FL26_Mod\work\face_pipeline\track_user1'
photo = cv2.imdecode(np.fromfile(BASE + r'\user1_tight.jpg', dtype=np.uint8), cv2.IMREAD_COLOR)
rend = cv2.imread(BASE + r'\relight\render_full_v3\v3_front.png')
ph, pw = photo.shape[:2]
rh, rw = rend.shape[:2]

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

Lp = detect(photo, 0.4)
Lr = detect(rend, 0.05)       # render needs a low threshold
if Lr is None or len(Lr) < 460:
    # fallback: manual eye boxes measured on the 800px render
    Lr = np.zeros((478, 2))
    Lr[33] = (300, 320); Lr[133] = (352, 322); Lr[362] = (452, 320); Lr[263] = (505, 318)
    Lr[1] = (400, 385); Lr[152] = (400, 470); Lr[10] = (400, 250)
    print('[overlay] MP failed on render -> manual eye boxes')

def eyes(L):
    return (L[33] + L[133]) / 2, (L[362] + L[263]) / 2
eLp, eRp = eyes(Lp); eLr, eRr = eyes(Lr)
# similarity photo->render from the two eye centers (+ scale from the distance)
vp = eRp - eLp; vr = eRr - eLr
scale = np.linalg.norm(vr) / np.linalg.norm(vp)
ang = np.arctan2(vr[1], vr[0]) - np.arctan2(vp[1], vp[0])
c, s = np.cos(ang), np.sin(ang)
A = np.zeros((2, 3))
A[:, :2] = scale * np.array([[c, -s], [s, c]])
A[:, 2] = (eLr + eRr) / 2 - A[:, :2] @ ((eLp + eRp) / 2)
print('[overlay] scale=%.2f rot=%.1f deg' % (scale, np.degrees(ang)))

warped = cv2.warpAffine(photo, A, (rw, rh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
# face oval mask in photo space -> warp
oval_idx = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
            152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
pm = np.zeros((ph, pw), np.uint8)
cv2.fillPoly(pm, [Lp[oval_idx].astype(np.int32)], 255)
pm = cv2.erode(pm, np.ones((9, 9), np.uint8))
wm = cv2.warpAffine(pm, A, (rw, rh), flags=cv2.INTER_LINEAR)
alpha = cv2.GaussianBlur(wmask.astype(np.float32) / 255.0 if False else wm.astype(np.float32) / 255.0, (0, 0), 6)[..., None]

blend = (rend * (1 - alpha) + warped * alpha).astype(np.uint8)
paste = (rend * (1 - alpha) + warped * alpha).astype(np.uint8)
paste2 = warped.copy(); paste2[alpha[..., 0] < 128] = rend[alpha[..., 0] < 128]  # opaque face paste
sheet = np.concatenate([
    cv2.resize(blend, (700, 700)),
    cv2.resize(paste2, (700, 700)),
    cv2.resize(rend, (700, 700))], axis=1)
sheet = cv2.cvtColor(sheet, cv2.COLOR_BGR2RGB)
Image.fromarray(sheet).save(BASE + r'\relight\overlay_direct.png')
print('[overlay] saved overlay_direct.png (blend | opaque paste | render)')