# -*- coding: utf-8 -*-
# bake10_full.py - FINAL clean pipeline (v17):
#   1. full-frame decal: photo face oval -> atlas face oval (the photo's
#      proportions fill the game's face area)
#   2. scalp hair paint (crown/back-of-head, dark short hair)
#   3. skin-tone harmonization (scalp/neck/ears follow the photo complexion)
#   4. measured piecewise row remap: nose -24, mouth -58, chin -38 texels
#      (the overlay-measured compression; features_uv follows the same map)
#   5. ball-swatch columns filled with skin (the eyeball triangles' swatch area
#      shows skin instead of default-eye fragments)
#   6. features_uv.json (geometry follows texture)
import json, os
import numpy as np
import cv2
from PIL import Image

sys_stdout = __import__('io').TextIOWrapper(__import__('sys').stdout.buffer, encoding='utf-8', errors='replace')
__import__('sys').stdout = sys_stdout

WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
PHOTO = os.path.join(WORK, 'user1_tight.jpg')
OUT = os.path.join(WORK, 'baked_full.png')
FEAT = os.path.join(WORK, 'features_uv.json')
TEX = 1024

img = cv2.imdecode(np.fromfile(PHOTO, dtype=np.uint8), cv2.IMREAD_COLOR)
assert img is not None
h, w = img.shape[:2]
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
TASK = 'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
o = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
    running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.4)
with vision.FaceLandmarker.create_from_options(o) as l:
    r = l.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
assert r.face_landmarks, 'no face'
L = np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64)
# ---- STRAIGHTEN: rotate the photo so the eye line is horizontal (about the
# eye midpoint); all landmarks rotate with it -> the decal inherits the level pose.
_eL = (L[33] + L[133]) / 2; _eR = (L[362] + L[263]) / 2
_theta = np.arctan2(_eR[1] - _eL[1], _eR[0] - _eL[0])
print('[v18] eye-line tilt %.2f deg -> straightening' % np.degrees(_theta))
_c = (_eL + _eR) / 2
_Mr = np.array([[np.cos(_theta), -np.sin(_theta)], [np.sin(_theta), np.cos(_theta)]])
_big = int(np.hypot(h, w) * 0.2) + 40
_Mr3 = np.zeros((2, 3))
_Mr3[:, :2] = _Mr
_Mr3[:, 2] = _c - _Mr @ _c + np.array([_big, _big])
img = cv2.warpAffine(img, _Mr3, (w + 2 * _big, h + 2 * _big), flags=cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(128, 128, 128))
L = (L - _c) @ _Mr.T + _c + np.array([_big, _big])
h, w = img.shape[:2]
MP = {'left_eye': [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
      'nose': [98, 327, 2], 'mouth': [0, 13, 14, 17],
      'left_brow': [105], 'right_brow': [334]}
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
             152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]

# ---- 1a. anchor fit (defines the atlas face region, from the baseline layout) ----
SK = json.load(open(os.path.join(WORK, 'skel_anchors.json')))
s = TEX / 512.0
EYE_DY = 13.5
def sk(n):
    dy = EYE_DY * s if 'eye' in n else 0.0
    return np.array([SK[n][0] * s, SK[n][1] * s + dy])
P = np.array([L[MP[n]].mean(0) for n in MP])
Q = np.array([sk(n) for n in MP])
Pc, Qc = P - P.mean(0), Q - Q.mean(0)
H = Pc.T @ Qc
U_, S_, Vt = np.linalg.svd(H)
dsgn = np.sign(np.linalg.det(Vt.T @ U_.T)) or 1.0
R = Vt.T @ np.diag([1.0, dsgn]) @ U_.T
scale = (S_ * dsgn).sum() / (Pc ** 2).sum()
A1 = np.zeros((2, 3))
A1[:, :2] = scale * R
A1[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
oval_photo = L[FACE_OVAL]
oval_atlas = np.c_[oval_photo, np.ones(len(oval_photo))] @ A1.T

# ---- 1b. full-frame paste: photo oval bbox -> atlas oval bbox ----
px0, px1 = oval_photo[:, 0].min(), oval_photo[:, 0].max()
py0, py1 = oval_photo[:, 1].min(), oval_photo[:, 1].max()
ax0, ax1 = oval_atlas[:, 0].min(), oval_atlas[:, 0].max()
ay0, ay1 = oval_atlas[:, 1].min(), oval_atlas[:, 1].max()
M2 = np.zeros((2, 3))
M2[0, 0] = (ax1 - ax0) / (px1 - px0)
M2[1, 1] = (ay1 - ay0) / (py1 - py0)
M2[0, 2] = (ax0 + ax1) / 2 - M2[0, 0] * (px0 + px1) / 2
M2[1, 2] = (ay0 + ay1) / 2 - M2[1, 1] * (py0 + py1) / 2
base = np.asarray(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB').resize((TEX, TEX), Image.LANCZOS), np.float64)
warped = cv2.warpAffine(img, M2, (TEX, TEX), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
pmask = np.zeros((h, w), np.uint8)
cv2.fillPoly(pmask, [oval_photo.astype(np.int32)], 255)
pmask = cv2.erode(pmask, np.ones((7, 7), np.uint8))
wmask = cv2.warpAffine(pmask, M2, (TEX, TEX), flags=cv2.INTER_LINEAR)
alpha = cv2.GaussianBlur(wmask.astype(np.float32) / 255.0, (0, 0), 4)[..., None]
out = base * (1 - alpha) + warped[..., ::-1].astype(np.float64) * alpha
print('[v17] paste done (sx=%.2f sy=%.2f)' % (M2[0, 0], M2[1, 1]))

# ---- 2. scalp hair paint ----
_EA = json.load(open('D:/FL26_Mod/work/face_pipeline/uv/mesh_ea1.json'))
_mV = np.asarray(_EA['vertices'], np.float64)
_mU = np.asarray(_EA['uv'], np.float64)
_mT = np.array([[t[0][0], t[1][0], t[2][0]] for t in _EA['triangles']], np.int64)
_hairv = ((_mV[:, 2] > 0.075) | ((_mV[:, 1] > 0.03) & (_mV[:, 2] > -0.03))) & (np.abs(_mV[:, 0]) <= 0.075)
_hm = np.zeros((TEX, TEX), np.float32)
for _t in _mT[np.all(_hairv[_mT], axis=1)]:
    _p = np.stack([_mU[_t, 0] % 1.0 * TEX, (1 - _mU[_t, 1] % 1.0) * TEX], 1)
    cv2.fillPoly(_hm, [_p.astype(np.int32)], 1.0)
_hm = np.clip(cv2.GaussianBlur(_hm, (0, 0), 9) * 1.18, 0, 1)
_rng = np.random.default_rng(7)
_haircol = np.array([38.0, 30.0, 26.0])[None, None, :] + (_rng.random((TEX, TEX, 1)) - 0.5) * 14
out = out * (1 - _hm[..., None]) + _haircol * _hm[..., None]
print('[v17] hair painted')

# ---- 3. skin-tone harmonization ----
_oval_in = cv2.erode(wmask, np.ones((31, 31), np.uint8)) > 0
_ring = (wmask > 40) & ~_oval_in
if _ring.sum() > 50:
    ps = warped[..., ::-1][_ring].mean(0)
    bs = base[_ring].mean(0)
    ratio = np.clip(ps / np.maximum(bs, 1), 0.55, 1.8)
else:
    ratio = np.array([1.0, 1.0, 1.0])
_tint = (1 - alpha) * ratio[None, None, :] + alpha * np.ones((1, 1, 3))
out = out * _tint
print('[v17] skin tint', np.round(ratio, 3))

# ---- 4. measured piecewise row remap (compression, no double exposure) ----
# M2-mapped feature rows (before remap)
_row = lambda n: float((np.c_[L[MP[n]].mean(0)[None], np.ones(1)] @ M2.T)[0, 1])
_Lall = {**MP, 'chin': [152], 'forehead': [10]}
_row = lambda n: float((np.c_[L[_Lall[n]].mean(0)[None], np.ones(1)] @ M2.T)[0, 1])
_r_nose, _r_mouth, _r_chin = _row('nose'), _row('mouth'), _row('chin')
# auto-calibration: deltas.json (blend - render, px) x 1.76 texels/px
_dj = {}
_djf = os.path.join(WORK, 'deltas.json')
if os.path.exists(_djf):
    _dj = json.load(open(_djf))
    print('[v18] auto-calibrating from deltas.json:', {k: [round(v[0],1), round(v[1],1)] for k, v in _dj.items()})
_upx_inv = 220.0 / 125.0                                    # atlas texels per render px
# EYE-ROW ANCHOR: rows above the eyes are IDENTITY (brows/eye content never
# move -> no dark crescents over the iris); compression lives between the eyes
# and the mouth/chin only.
_eyety = 351.0
_ctrl_old = np.array([0.0, _eyety, _r_nose, _r_mouth, _r_chin, float(TEX)])
_ctrl_new = _ctrl_old.copy()
if _dj:
    _ctrl_new[2] += _dj.get('nose_tip', [0, 0])[1] * _upx_inv
    _ctrl_new[3] += _dj.get('lip_top', _dj.get('mouth_L', [0, 0]))[1] * _upx_inv
    _ctrl_new[4] += _dj.get('chin', [0, 0])[1] * _upx_inv
if _dj:
    _ctrl_new[1] += _dj.get('nose_tip', [0, 0])[1] * _upx_inv
    _ctrl_new[2] += _dj.get('lip_top', _dj.get('mouth_L', [0, 0]))[1] * _upx_inv
    _ctrl_new[3] += _dj.get('chin', [0, 0])[1] * _upx_inv
print('[v18] remap rows: nose %.0f->%.0f mouth %.0f->%.0f chin %.0f->%.0f' % (
    _ctrl_old[1], _ctrl_new[1], _ctrl_old[2], _ctrl_new[2], _ctrl_old[3], _ctrl_new[3]))
_rows = np.arange(TEX)
_src_ty = np.interp(_rows, _ctrl_new, _ctrl_old)
_i0 = np.clip(_src_ty.astype(int), 0, TEX - 2)
_w = (_src_ty - _i0)[..., None]
out = out[_i0] * (1 - _w) + out[_i0 + 1] * _w
print('[v17] row remap applied')

# ---- 5. ball-swatch columns -> skin ----
_skin = out[620:660, 480:560].mean(0).mean(0)
for _x0, _x1 in [(0, 268), (756, TEX)]:
    _rr = np.zeros((TEX, TEX), np.float32)
    _rr[180:830, _x0:_x1] = 1.0
    _rr = cv2.GaussianBlur(_rr, (0, 0), 8)[..., None]
    _keep = ((1 - _hm) * _rr[..., 0])[..., None]
    out = out * (1 - _keep) + np.zeros((TEX, TEX, 3), np.float64) + _skin[None, None, :] * _keep
print('[v17] swatch skin fill done')

Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT)
print('[v17] saved', OUT)

# ---- 6. features_uv (through the same row remap) ----
feat = {}
for n in MP:
    fu = np.c_[L[MP[n]].mean(0)[None], np.ones(1)] @ M2.T
    feat[n] = [float(fu[0, 0]), float(fu[0, 1])]
for n, ix in [('chin', 152), ('forehead', 10), ('cheek_L', 234), ('cheek_R', 454)]:
    fu = np.c_[L[ix][None], np.ones(1)] @ M2.T
    feat[n] = [float(fu[0, 0]), float(fu[0, 1])]
for _k in feat:
    feat[_k][1] = float(np.interp(feat[_k][1], _ctrl_new, _ctrl_old))
feat['oval_atlas'] = oval_atlas.tolist()
json.dump(feat, open(FEAT, 'w'))
print('[v17] features_uv:', {k: [round(v[0]), round(v[1])] for k, v in feat.items() if k != 'oval_atlas'})