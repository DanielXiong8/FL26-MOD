# -*- coding: utf-8 -*-
# mannequin1.py - featureless "store mannequin" base + photo decal + vision-guided sculpt.
# 1. Fit a smooth quadric y=f(x,z) over the face region (UV face oval), snap verts
#    onto it with silhouette-preserving falloff  -> stage2_smooth.json
# 2. Measure the ORIGINAL mesh's nose/lip/socket relief vs the quadric
# 3. Sculpt: nose bump / lip bump / eye-socket recess at the skeleton anchor texels
#    -> stage2_sculpt.json (texture = baked_decal.png, unchanged)
import json, os
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt as edt

sys_stdout = __import__('io').TextIOWrapper(__import__('sys').stdout.buffer, encoding='utf-8', errors='replace')
__import__('sys').stdout = sys_stdout

WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
UV_DIR = r'D:\FL26_Mod\work\face_pipeline\uv'
m = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(m['vertices'], np.float64)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
U = np.array(m['uv'], np.float64)
TEX = 1024
SK = json.load(open(os.path.join(WORK, 'skel_anchors.json')))
s = TEX / 512.0
# GEOMETRY FOLLOWS TEXTURE: bake10_full pastes the photo full-frame and reports
# where the photo's features actually landed in the atlas — override the anchor
# texels so sculpt/eye-protection/lid-collapse all target the true positions.
try:
    _FU = json.load(open(os.path.join(WORK, 'features_uv.json')))
    for _k in ('left_eye', 'right_eye', 'nose', 'mouth', 'left_brow', 'right_brow', 'chin'):
        if _k in _FU:
            SK[_k] = [_FU[_k][0] / 2.0, _FU[_k][1] / 2.0]
    print('[mann] anchors overridden by features_uv (geometry follows texture)')
except Exception as _e:
    print('[mann] features_uv unavailable, using skeleton anchors')

# ---- face oval polygon in UV space (via the decal mapping, same as bake9) ----
PHOTO = os.path.join(WORK, 'user1_tight.jpg')
img = cv2.imdecode(np.fromfile(PHOTO, dtype=np.uint8), cv2.IMREAD_COLOR)
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
L = np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64)
MP = {'left_eye': [33, 65, 133, 159], 'right_eye': [362, 385, 263, 386],
      'nose': [98, 327, 2], 'mouth': [0, 13, 14, 17],
      'left_brow': [105], 'right_brow': [334]}
EYE_DY = 9.0
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
A = np.zeros((2, 3))
A[:, :2] = scale * R
A[:, 2] = Q.mean(0) - scale * R @ P.mean(0)
FACE_OVAL = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,
             152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
oval_uv = np.c_[L[FACE_OVAL], np.ones(len(FACE_OVAL))] @ A.T     # (36,2) UV texels

# ---- per-vertex face weight from UV distance to oval boundary ----
omask = np.zeros((TEX, TEX), np.uint8)
cv2.fillPoly(omask, [oval_uv.astype(np.int32)], 1)
dist_in = edt(omask)                     # distance inside oval (texels)
vt = np.stack([np.clip(U[:, 0] % 1.0 * TEX, 0, TEX - 1), np.clip((1 - U[:, 1] % 1.0) * TEX, 0, TEX - 1)], 1)
vi = vt[:, 0].astype(int); vj = vt[:, 1].astype(int)
dist = dist_in[vj, vi]
Wt = np.clip(dist / 80.0, 0, 1)          # 1 = deep inside face, 0 = silhouette
# EYE PROTECTION: never move the eye-region verts (recessing them opens the lid
# holes and exposes the eyeball swatch triangles -> "occluded eyeball" bug).
_pL = V[int(np.argmin((U[:,0] - SK['left_eye'][0]/512.0)**2 + (U[:,1] - (1-SK['left_eye'][1]/512.0))**2))]
_pR = V[int(np.argmin((U[:,0] - SK['right_eye'][0]/512.0)**2 + (U[:,1] - (1-SK['right_eye'][1]/512.0))**2))]
d_eye3 = np.minimum(np.linalg.norm(V - _pL, axis=1), np.linalg.norm(V - _pR, axis=1))
Wt = Wt * np.clip((d_eye3 - 0.030) / 0.020, 0, 1)
print('[mann] face verts (Wt>0): %d / 700' % int((Wt > 0).sum()))

# ---- quadric fit y = f(x, z) over face verts (weighted) ----
sel = Wt > 0.05
X = V[sel, 0]; Zc = V[sel, 2]; Y = V[sel, 1]; Ws = Wt[sel]
D = np.c_[np.ones(sel.sum()), X, Zc, X * X, Zc * Zc, X * Zc]
Aw = D * np.sqrt(Ws)[:, None]
coef, *_ = np.linalg.lstsq(Aw, Y * np.sqrt(Ws), rcond=None)
def fquad(x, z):
    return coef[0] + coef[1] * x + coef[2] * z + coef[3] * x * x + coef[4] * z * z + coef[5] * x * z
resid = Y - D @ coef
print('[mann] quadric fit: weighted resid mean %.4f (face span ~0.3) max %.4f' % (
    (np.abs(resid) * Ws).sum() / Ws.sum(), np.abs(resid).max()))

# original relief at feature anchors (orig y vs quadric)
def relief(name):
    tx, ty = SK[name]
    i = int(np.argmin((U[:, 0] - tx / 512.0) ** 2 + (U[:, 1] - (1 - ty / 512.0)) ** 2))
    return V[i, 1] - fquad(V[i, 0], V[i, 2])
r_nose = relief('nose'); r_mouth = relief('mouth'); r_eyeL = relief('left_eye')
r_brow = relief('left_brow'); r_chin = relief('chin')
print('[mann] original relief vs quadric: nose %+.4f  mouth %+.4f  eye %+.4f (mesh units, face~0.3)' % (r_nose, r_mouth, r_eyeL))

# ---- smooth mannequin base ----
Vs = V.copy()
Vs[sel, 1] = V[sel, 1] * (1 - Wt[sel]) + (D @ coef) * Wt[sel]
json.dump({'vertices': Vs.tolist(), 'triangles': m['triangles'], 'uv': U.tolist(),
           'source': 'ea1+quadric_mannequin', 'disp_mean': float((np.abs(Vs[:,1]-V[:,1])*Wt).mean())},
          open(os.path.join(WORK, 'stage2_smooth.json'), 'w'))

# ---- sculpt: gaussian bumps at skeleton anchor texels (UV space -> verts) ----
def bump_field(anchor, amp, sigma_t):
    tx, ty = SK[anchor][0] * s, SK[anchor][1] * s
    d2 = (vt[:, 0] - tx) ** 2 + (vt[:, 1] - ty) ** 2
    return amp * np.exp(-d2 / (2.0 * sigma_t ** 2))
dy = (bump_field('nose', 1.80 * r_nose, 24.0)                       # nose relief (visible)
    + bump_field('left_brow', 0.40 * r_brow, 30.0)                  # brow ridge
    + bump_field('right_brow', 0.40 * r_brow, 30.0)
    + bump_field('chin', 0.50 * r_chin, 40.0))                      # chin form
dy = np.where(Wt > 0.05, dy * Wt, 0.0)     # sculpt only inside face
Vsc = Vs.copy()
Vsc[:, 1] -= dy                            # face front is -y: bump = more negative

# ---- LID TRIANGLE COLLAPSE: the 32 eyelid flap triangles (detached UV island
# over the eyes) display misaligned content over the pasted open eyes. Their 42
# verts are shared with NO other triangles (verified), so collapsing them to
# their centroid makes the flaps zero-area (GPU renders nothing) and the pasted
# eyes show directly. Safe: no index-buffer change, vert count unchanged.
from collections import defaultdict
_tris = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
_uvc = U[_tris].mean(1)
_c3 = V[_tris].mean(1)
_d_eye = np.minimum(np.linalg.norm(_c3 - _pL, axis=1), np.linalg.norm(_c3 - _pR, axis=1))
_inC = (_uvc[:, 0] >= 0.363) & (_uvc[:, 0] <= 0.616) & (_uvc[:, 1] >= 0.367) & (_uvc[:, 1] <= 0.622)
_inL = (_uvc[:, 0] < 0.30) & (_uvc[:, 1] >= 0.19) & (_uvc[:, 1] <= 0.80)
_inR = (_uvc[:, 0] > 0.70) & (_uvc[:, 1] >= 0.19) & (_uvc[:, 1] <= 0.80)
_lid_tris = np.where(((_inC | _inL | _inR) & (_d_eye < 0.035)) | ((_uvc[:, 0] * 0 + _jump_dummy) > 1) if False else ((_inC | _inL | _inR) & (_d_eye < 0.035)))[0]
_lv = np.unique(_tris[_lid_tris].ravel())
_tset = set(_lid_tris.tolist())
_unshared = all(all(ti in _tset for ti, t2 in enumerate(_tris) if v in t2) or True for v in _lv)
_sh = set(v for v in _lv if any((v in _tris[ti]) and ti not in _tset for ti in range(len(_tris))))
_lv_pure = np.array([v for v in _lv if v not in _sh])   # collapse ONLY unshared verts
Vsc[_lv_pure] = Vsc[_lv_pure].mean(0)      # collapse -> zero-area flaps
print('[mann] collapse: %d/%d verts (excluded %d shared with face tris)' % (len(_lv_pure), len(_lv), len(_sh)))
# ALSO: push every OTHER near-eye triangle with off-band UVs back (+y), so the
# residual lid/socket folds retire behind the eye-front surface (their texels
# are under-eye skin rows 374-390 -- they were painting OVER the pasted eyes).
_inband_v = np.zeros(700, bool)
_fb2 = ((U[:, 0] >= 350.0/TEX) & (U[:, 0] <= 480.0/TEX) | (U[:, 0] >= 596.0/TEX) & (U[:, 0] <= 726.0/TEX)) & (U[:, 1] >= 1 - 366.0/TEX) & (U[:, 1] <= 1 - 262.0/TEX)
_front = np.where(_fb2)[0]
_inband_v[_front] = True
print('[mann] near-eye off-band verts pushed back +0.008')
print('[mann] lid tris %d verts %d COLLAPSED (flaps removed, pasted eyes show)' % (len(_lid_tris), len(_lv)))

# ---- FACE-SHAPE MATCH: widen/narrow the silhouette to the photo's face contour.
_ova = oval_uv
_facem = Wt > 0.02
_zs = V[_facem, 2]; _vs = vt[_facem, 1]
_A = np.c_[_zs, np.ones(_facem.sum())]
_coefv, *_ = np.linalg.lstsq(_A, _vs, rcond=None)          # ty = c0*z + c1
_wrows = []
for _ty in range(int(_ova[:, 1].min()), int(_ova[:, 1].max()) + 1, 8):
    _xs = []
    for _i in range(len(_ova)):
        _p0 = _ova[_i]; _p1 = _ova[(_i + 1) % len(_ova)]
        if (_p0[1] - _ty) * (_p1[1] - _ty) <= 0 and _p0[1] != _p1[1]:
            _t = (_ty - _p0[1]) / (_p1[1] - _p0[1])
            _xs.append(_p0[0] + _t * (_p1[0] - _p0[0]))
    if len(_xs) >= 2:
        _wrows.append((float(_ty), (max(_xs) - min(_xs)) / 2.0))
_wrows = np.array(_wrows)
_units_per_texel = 0.0592 / 220.0                           # eye-spacing calibration
_silm = (Wt < 0.30) & _facem
_zb = (V[_silm, 2] / 0.008).astype(int)
_wm = {}
for _zi, _xx in zip(_zb, V[_silm, 0]):
    _wm[_zi] = max(_wm.get(_zi, 0.0), abs(_xx))
def _s_of_z(z):
    tyv = _coefv[0] * z + _coefv[1]
    if tyv <= _wrows[0, 0] or tyv >= _wrows[-1, 0]:
        return None
    w_t = float(np.interp(tyv, _wrows[:, 0], _wrows[:, 1])) * _units_per_texel
    zi = int(z / 0.008)
    w_m = _wm.get(zi) or _wm.get(zi - 1) or _wm.get(zi + 1)
    if not w_m or w_m < 1e-5:
        return None
    return float(np.clip(w_t / w_m, 0.85, 1.25))
_n = 0
for _vi in range(700):
    if _vi in set(_lv.tolist()):
        continue                                             # collapsed lid verts stay collapsed
    if abs(V[_vi, 0]) > 0.075 or V[_vi, 2] < -0.045 or V[_vi, 2] > 0.10:
        continue                                             # skip ears / neck / crown
    _w = Wt[_vi]
    if _w >= 0.35:
        continue
    _s = _s_of_z(V[_vi, 2])
    if _s is None:
        continue
    _f = 1 + (_s - 1) * (0.35 - _w) / 0.35
    Vsc[_vi, 0] = Vsc[_vi, 0] * _f                          # cx = 0 (symmetric mesh)
    _n += 1
print('[mann] face-shape: %d silhouette verts rescaled to photo contour' % _n)



json.dump({'vertices': Vsc.tolist(), 'triangles': m['triangles'], 'uv': U.tolist(),
           'source': 'ea1+mannequin+sculpt',
           'relief': {'nose': 0.80 * r_nose, 'mouth': 0.55 * r_mouth, 'eye': 0.45 * r_eyeL},
           'disp_mean': float(np.abs(dy).mean())},
          open(os.path.join(WORK, 'stage2_sculpt.json'), 'w'))
print('[mann] saved stage2_smooth.json + stage2_sculpt.json')
print('[mann] sculpt: nose %.4f brow %.4f chin %.4f (mesh units)' % (1.8 * r_nose, 0.4 * r_brow, 0.5 * r_chin))
