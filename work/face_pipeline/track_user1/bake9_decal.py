# -*- coding: utf-8 -*-
# bake9_decal.py - HARD face decal: paste the photo's face straight onto the game
# UV texture, guided ONLY by the skeleton anchors (baseline feature texels).
# No render-plane sampling, no lighting-ratio, no per-triangle machinery.
# Brightness = photo as-is.
import json, os
import numpy as np
import cv2
from PIL import Image

sys_stdout = __import__('io').TextIOWrapper(__import__('sys').stdout.buffer, encoding='utf-8', errors='replace')
__import__('sys').stdout = sys_stdout

WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
PHOTO = os.path.join(WORK, 'user1_tight.jpg')
OUT = os.path.join(WORK, 'baked_decal.png')
TEX = 1024

img = cv2.imdecode(np.fromfile(PHOTO, dtype=np.uint8), cv2.IMREAD_COLOR)
assert img is not None
h, w = img.shape[:2]
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
TASK = r'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'
rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
o = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
    running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.4)
with vision.FaceLandmarker.create_from_options(o) as l:
    r = l.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
assert r.face_landmarks, 'no face'
L = np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64)
print('[decal] photo', w, 'x', h)

# skeleton anchors (baseline texels, 512-grid) -> UV texels at TEX
SK = json.load(open(os.path.join(WORK, 'skel_anchors.json')))
s = TEX / 512.0
EYE_DY = 13.5   # MP eye center -> atlas eye-band vertical center (143..172 -> 157.5)   # MP eye = eye CENTER; baseline dark cluster = lash line (above iris)
def sk(n):
    dy = EYE_DY * s if 'eye' in n else 0.0
    return np.array([SK[n][0] * s, SK[n][1] * s + dy])

MP = {
    'left_eye':  [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
    'nose':      [98, 327, 2],       'mouth':     [0, 13, 14, 17],
    'left_brow': [105],              'right_brow':[334],
}
P = np.array([L[MP[n]].mean(0) for n in MP])       # photo px
Q = np.array([sk(n) for n in MP])                  # uv texels

# similarity photo -> UV (Procrustes)
Pc, Qc = P - P.mean(0), Q - Q.mean(0)
H = Pc.T @ Qc
U_, S_, Vt = np.linalg.svd(H)
d = np.sign(np.linalg.det(Vt.T @ U_.T)) or 1.0
R = Vt.T @ np.diag([1.0, d]) @ U_.T
scale = (S_ * d).sum() / (Pc ** 2).sum()
A = np.zeros((2, 3))
A[:, :2] = scale * R
A[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
fit = (scale * R @ Pc.T).T - Qc
per = np.hypot(fit[:, 0], fit[:, 1])
for n, e in zip(MP, per):
    print('  %-10s %.1f texel' % (n, e))
print('similarity: scale=%.2f rot=%.2f deg, mean=%.1f texel' % (
    scale, np.degrees(np.arctan2(R[1, 0], R[0, 0])), per.mean()))

# face oval region in photo space -> warp -> paste
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
             152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
oval = L[FACE_OVAL].astype(np.int32)
pmask = np.zeros((h, w), np.uint8)
cv2.fillPoly(pmask, [oval], 255)
pmask = cv2.erode(pmask, np.ones((9, 9), np.uint8))

base = np.asarray(Image.open(os.path.join(WORK, 'baseline_eastasia_new1.png')).convert('RGB').resize((TEX, TEX), Image.LANCZOS), np.float64)
warped = cv2.warpAffine(img, A, (TEX, TEX), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)
wmask = cv2.warpAffine(pmask, A, (TEX, TEX), flags=cv2.INTER_LINEAR)
alpha = cv2.GaussianBlur(wmask.astype(np.float32) / 255.0, (0, 0), 3)[..., None]
out = base * (1 - alpha) + warped[..., ::-1].astype(np.float64) * alpha

# ---- skin-tone harmonization: tint the NON-decal atlas (scalp/neck/ears) so
# the whole head matches the photo's complexion instead of the baseline tan.
_oval_in = cv2.erode(wmask, np.ones((31, 31), np.uint8)) > 0     # deep inside decal = photo skin
_ring = (wmask > 40) & ~_oval_in                                  # decal edge ring = same skin in both
if _ring.sum() > 50:
    photo_skin = warped[..., ::-1][_ring].mean(0)                 # RGB
    base_skin = base[_ring].mean(0)
    ratio = np.clip(photo_skin / np.maximum(base_skin, 1), 0.55, 1.8)
else:
    ratio = np.array([1.0, 1.0, 1.0])
print('[decal] skin tint ratio (RGB):', np.round(ratio, 3))
_tint = (1 - alpha[..., 0])[..., None] * ratio[None, None, :] + alpha[..., 0][..., None] * np.ones_like(ratio)[None, None, :]
out = out * _tint
# ---- scalp hair paint: cover the scalp/back-of-head with dark short hair.
import json as _j
_mm = _j.load(open('D:/FL26_Mod/work/face_pipeline/uv/mesh_ea1.json'))
_mV = np.asarray(_mm['vertices'], np.float64)
_mU = np.asarray(_mm['uv'], np.float64)
_mT = np.array([[t[0][0], t[1][0], t[2][0]] for t in _mm['triangles']], np.int64)
_hairv = ((_mV[:, 2] > 0.075) | ((_mV[:, 1] > 0.03) & (_mV[:, 2] > -0.03))) & (np.abs(_mV[:, 0]) <= 0.075)
_hm = np.zeros((TEX, TEX), np.float32)
_htri = _mT[np.all(_hairv[_mT], axis=1)]
for _t in _htri:
    _p = np.stack([_mU[_t, 0] % 1.0 * TEX, (1 - _mU[_t, 1] % 1.0) * TEX], 1)
    cv2.fillPoly(_hm, [_p.astype(np.int32)], 1.0)
_hm = cv2.GaussianBlur(_hm, (0, 0), 9)
_hm = np.clip(_hm * 1.18, 0, 1)[..., None]
_rng = np.random.default_rng(7)
_noise = (_rng.random((TEX, TEX, 1)) - 0.5) * 14
_haircol = np.array([38.0, 30.0, 26.0])[None, None, :] + _noise
out = out * (1 - _hm) + _haircol * _hm
print('[decal] scalp hair painted: %d tri, %.1f%% of atlas' % (len(_htri), _hm.mean() * 100))
# ---- EYEBALL REPAINT: the visible eyeballs = ball triangles through the eye
# holes, sampling atlas edge swatches. Paint the photo's own iris+sclera at the
# forward-visible UV spots (L: u=.214 v=.496, R: u=.764 v=.496); C strip (inner
# corners) gets periorbital skin (it was showing photo-mouth chunks).
def _disc_mask(cu, cv_, r, soft=6):
    _cx, _cy = cu * TEX, (1 - cv_) * TEX
    _yy, _xx = np.mgrid[0:TEX, 0:TEX]
    _d = np.sqrt((_xx - _cx) ** 2 + (_yy - _cy) ** 2)
    _m = np.clip((r - _d) / (2 * soft) + 0.5, 0, 1)
    return _m[..., None]
def _eye_crop(side, scale):
    _c = L[MP[side + '_eye']].mean(0)
    _r = int(np.linalg.norm(L[33] - L[133]) * 0.36 * scale)
    _x0, _y0 = int(_c[0] - _r), int(_c[1] - _r)
    _c0 = img[_y0:_y0 + 2 * _r, _x0:_x0 + 2 * _r]
    _c0 = cv2.cvtColor(_c0, cv2.COLOR_BGR2RGB)
    return cv2.resize(_c0, (2 * 30, 2 * 30), interpolation=cv2.INTER_LANCZOS4).astype(np.float64)
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(OUT)
print('[decal] saved', OUT)
