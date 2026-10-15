# -*- coding: utf-8 -*-
# bake10_full.py - FULL-FRAME decal: the photo's face FILLS the entire atlas face
# region (oval-to-oval stretch), NOT anchor-aligned to the baseline layout.
# The photo's proportions win; the mannequin geometry follows (features_uv.json).
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
MP = {'left_eye': [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
      'nose': [98, 327, 2], 'mouth': [0, 13, 14, 17],
      'left_brow': [105], 'right_brow': [334]}
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
             152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]

# ---- atlas face region: the baseline-layout oval (anchor fit, kept from v13) ----
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
d = np.sign(np.linalg.det(Vt.T @ U_.T)) or 1.0
R = Vt.T @ np.diag([1.0, d]) @ U_.T
scale = (S_ * d).sum() / (Pc ** 2).sum()
A1 = np.zeros((2, 3))
A1[:, :2] = scale * R
A1[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
oval_photo = L[FACE_OVAL]
oval_atlas = np.c_[oval_photo, np.ones(len(oval_photo))] @ A1.T   # atlas face region polygon

# ---- FULL-FRAME paste: photo oval bbox -> atlas oval bbox (non-uniform fill) ----
px0, px1 = oval_photo[:, 0].min(), oval_photo[:, 0].max()
py0, py1 = oval_photo[:, 1].min(), oval_photo[:, 1].max()
ax0, ax1 = oval_atlas[:, 0].min(), oval_atlas[:, 0].max()
ay0, ay1 = oval_atlas[:, 1].min(), oval_atlas[:, 1].max()
M2 = np.zeros((2, 3))
M2[0, 0] = (ax1 - ax0) / (px1 - px0)
M2[1, 1] = (ay1 - ay0) / (py1 - py0)
M2[0, 2] = (ax0 + ax1) / 2 - M2[0, 0] * (px0 + px1) / 2
M2[1, 2] = (ay0 + ay1) / 2 - M2[1, 1] * (py0 + py1) / 2
print('[full] photo bbox %.0fx%.0f -> atlas bbox %.0fx%.0f (sx=%.2f sy=%.2f)' % (
    px1 - px0, py1 - py0, ax1 - ax0, ay1 - ay0, M2[0, 0], M2[1, 1]))

base = np.asarray(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB').resize((TEX, TEX), Image.LANCZOS), np.float64)
warped = cv2.warpAffine(img, M2, (TEX, TEX), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
pmask = np.zeros((h, w), np.uint8)
cv2.fillPoly(pmask, [oval_photo.astype(np.int32)], 255)
pmask = cv2.erode(pmask, np.ones((7, 7), np.uint8))
wmask = cv2.warpAffine(pmask, M2, (TEX, TEX), flags=cv2.INTER_LINEAR)
alpha = cv2.GaussianBlur(wmask.astype(np.float32) / 255.0, (0, 0), 4)[..., None]
out = base * (1 - alpha) + warped[..., ::-1].astype(np.float64) * alpha

Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(r'D:/FL26_Mod/work/face_pipeline/track_user1/relight/stage_0_blend.png')
# ---- skin-tone harmonization (scalp/neck/ears follow the photo complexion) ----
_oval_in = cv2.erode(wmask, np.ones((31, 31), np.uint8)) > 0
_ring = (wmask > 40) & ~_oval_in
if _ring.sum() > 50:
    ps = warped[..., ::-1][_ring].mean(0)
    bs = base[_ring].mean(0)
    ratio = np.clip(ps / np.maximum(bs, 1), 0.55, 1.8)
else:
    ratio = np.array([1.0, 1.0, 1.0])
print('[full] skin tint ratio:', np.round(ratio, 3))
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(r'D:/FL26_Mod/work/face_pipeline/track_user1/relight/stage_A_paste.png')
_tint = (1 - alpha[..., 0])[..., None] * ratio[None, None, :] + alpha[..., 0][..., None]
out = out * _tint

# ---- scalp hair paint ----
_mm = json.load(open('D:/FL26_Mod/work/face_pipeline/uv/mesh_ea1.json'))
_mV = np.asarray(_mm['vertices'], np.float64)
_mU = np.asarray(_mm['uv'], np.float64)
_mT = np.array([[t[0][0], t[1][0], t[2][0]] for t in _mm['triangles']], np.int64)
_hairv = ((_mV[:, 2] > 0.075) | ((_mV[:, 1] > 0.03) & (_mV[:, 2] > -0.03))) & (np.abs(_mV[:, 0]) <= 0.075)
_hm = np.zeros((TEX, TEX), np.float32)
for _t in _mT[np.all(_hairv[_mT], axis=1)]:
    _p = np.stack([_mU[_t, 0] % 1.0 * TEX, (1 - _mU[_t, 1] % 1.0) * TEX], 1)
    cv2.fillPoly(_hm, [_p.astype(np.int32)], 1.0)
_hm = np.clip(cv2.GaussianBlur(_hm, (0, 0), 9) * 1.18, 0, 1)[..., None]
_rng = np.random.default_rng(7)
_haircol = np.array([38.0, 30.0, 26.0])[None, None, :] + (_rng.random((TEX, TEX, 1)) - 0.5) * 14
out = out * (1 - _hm) + _haircol * _hm

# ---- MEASURED FEATURE SHIFTS as a PIECEWISE-LINEAR ROW REMAP (compression,
# no double exposure): control rows = (0, nose, mouth, chin, TEX) -> shifted.
_ctrl_old = np.array([0.0, 489.0, 571.0, 712.0, float(TEX)])
_ctrl_new = np.array([0.0, 489.0 - 24.1, 571.0 - 58.3, 712.0 - 38.5, float(TEX)])
_rows = np.arange(TEX)
_src_ty = np.interp(_rows, _ctrl_new, _ctrl_old)          # display row r <- source row
_i0 = np.clip(_src_ty.astype(int), 0, TEX - 1)
_i1 = np.clip(_i0 + 1, 0, TEX - 1)
_w = (_src_ty - _i0)[..., None]
out = out * (1 - _w) + out[_i1] * _w                       # per-row bilinear resample
out = out[::-1] * 0 + out                                  # no-op keep dtype
print('[full] piecewise row remap applied (nose -24, mouth -58, chin -38 texels)')
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save('relight/baked_preremap.png')

# ---- SYNTHESIZED EYEBALLS: radial-gradient eyes painted at the ball swatches'
# forward-visible spots (L u=.214, R u=.764, both v=.496). Colors sampled from
# the photo (sclera beside the iris, iris at the eye center). No rectangles.
def _rad(cu, cvv):
    _cx, _cy = cu * TEX, (1 - cvv) * TEX
    _yy, _xx = np.mgrid[0:TEX, 0:TEX]
    return np.sqrt((_xx - _cx) ** 2 + (_yy - _cy) ** 2)
for _side, _cu in [('left', 0.214), ('right', 0.764)]:
    _ec = L[MP[_side + '_eye']].mean(0)
    _ew = (np.linalg.norm(L[33] - L[133]) if _side == 'left' else np.linalg.norm(L[362] - L[263]))
    _ir = int(_ew * 0.16)                        # iris radius px in photo
    _iris_c = img[int(_ec[1]) - _ir:int(_ec[1]) + _ir, int(_ec[0]) - _ir:int(_ec[0]) + _ir]
    _iris_c = cv2.cvtColor(_iris_c, cv2.COLOR_BGR2RGB)
    _yy, _xx = np.mgrid[:_iris_c.shape[0], :_iris_c.shape[1]]
    _rr = np.sqrt((_xx - _ir) ** 2 + (_yy - _ir) ** 2)
    _iris_col = _iris_c[(_rr < _ir * 0.8)].mean(0)          # iris avg color
    _pup_col = _iris_c[(_rr < _ir * 0.3)].mean(0)           # pupil avg color
    _scl_x = int(_ec[0] + (1 if _side == 'left' else -1) * _ew * 0.55)
    _sclera_col = cv2.cvtColor(img[int(_ec[1]) - 6:int(_ec[1]) + 6, max(_scl_x - 6, 0):_scl_x + 6],
                               cv2.COLOR_BGR2RGB).mean(0).mean(0)
    _R = _rad(_cu, 0.496)
    _mAll = np.clip((58 - _R) / 10.0, 0, 1)[..., None]       # swatch paint extent
    _mIri = np.clip((26 - _R) / 6.0, 0, 1)[..., None]        # iris
    _mPup = np.clip((9 - _R) / 4.0, 0, 1)[..., None]         # pupil
    _eye = np.zeros((TEX, TEX, 3), np.float64) + _sclera_col[None, None, :]
    _eye = _eye * (1 - _mIri) + _iris_col[None, None, :] * _mIri
    _eye = _eye * (1 - _mPup) + _pup_col[None, None, :] * _mPup
    out = out * (1 - _mAll) + _eye * _mAll
print('[full] synthesized eyeballs painted')
# ---- L/R swatch skin fill: the ball triangles' whole swatch columns become
# skin (matching the tinted complexion), so any visible part of the balls reads
# as skin, never as grey fragments. Hair mask protected.
_hm = np.zeros((TEX, TEX), np.float32)
for _t in _mT[np.all(_hairv[_mT], axis=1)]:
    _p = np.stack([_mU[_t, 0] % 1.0 * TEX, (1 - _mU[_t, 1] % 1.0) * TEX], 1)
    cv2.fillPoly(_hm, [_p.astype(np.int32)], 1.0)
_hm = np.clip(cv2.GaussianBlur(_hm, (0, 0), 9) * 1.18, 0, 1)
_skin = out[600:640, 480:560].mean(0).mean(0)          # tinted chin skin sample
for _x0, _x1 in [(0, 268), (756, TEX)]:
    _rr = np.zeros((TEX, TEX), np.float32)
    _rr[180:830, _x0:_x1] = 1.0
    _rr = cv2.GaussianBlur(_rr, (0, 0), 8)[..., None]
    _keep = (1 - _hm[..., None]) * _rr
    out = out * (1 - _keep) + np.zeros((TEX, TEX, 3), np.float64) + _skin[None, None, :] * _keep
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT)
print('[full] saved', OUT)

# ---- features_uv.json: where the photo's features landed in the atlas ----
feat = {}
for n in MP:
    fu = np.c_[L[MP[n]].mean(0)[None], np.ones(1)] @ M2.T
    feat[n] = [float(fu[0, 0]), float(fu[0, 1])]
for n, ix in [('chin', 152), ('forehead', 10), ('cheek_L', 234), ('cheek_R', 454)]:
    fu = np.c_[L[ix][None], np.ones(1)] @ M2.T
    feat[n] = [float(fu[0, 0]), float(fu[0, 1])]
_cmap_new = _ctrl_new; _cmap_old = _ctrl_old
for _k in ('nose', 'mouth', 'left_brow', 'right_brow', 'chin'):
    feat[_k][1] = float(np.interp(feat[_k][1], _cmap_old, _cmap_new))
feat['oval_atlas'] = oval_atlas.tolist()
json.dump(feat, open(FEAT, 'w'))
print('[full] features_uv:', {k: [round(v[0]), round(v[1])] for k, v in feat.items() if k != 'oval_atlas'})
