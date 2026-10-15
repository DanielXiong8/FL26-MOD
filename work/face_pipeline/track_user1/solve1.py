# -*- coding: utf-8 -*-
# solve1.py - UNIFIED target-driven warp: one dense (piecewise-affine) transform
# drives BOTH the texture and the geometry, so they can never desynchronize.
#   Target  = overlay composite (photo face pasted on the render = the truth)
#   Current = current render
#   Delaunay triangulation over MediaPipe landmarks; per-triangle affine from
#   current->target; texture resampled through it; every mesh vertex transformed
#   by the affine of the triangle its UV falls in (same map, same frame).
import json, os
import numpy as np
import cv2
from PIL import Image
from scipy.spatial import Delaunay

sys_stdout = __import__('io').TextIOWrapper(__import__('sys').stdout.buffer, encoding='utf-8', errors='replace')
__import__('sys').stdout = sys_stdout

WORK = r'D:\FL26_Mod\work\face_pipeline\track_user1'
TEX = 1024

blend = cv2.imread(WORK + r'\relight\overlay_direct.png')[:, 0:700]          # target
rend = cv2.imread(WORK + r'\relight\render_full_v3\v3_front.png')            # current
blend = cv2.resize(blend, (rend.shape[1], rend.shape[0]))
bake = np.asarray(Image.open(WORK + r'\baked_full.png').convert('RGB'), np.float64)

import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
TASK = 'D:/FL26_Mod/work/face_pipeline/face_landmarker_v2_with_blendshapes.task'

def detect(img, thr):
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    o = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
        running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=thr)
    with vision.FaceLandmarker.create_from_options(o) as l:
        r = l.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    return np.array([[p.x * w, p.y * h] for p in r.face_landmarks[0]], np.float64) if r.face_landmarks else None

Lb = detect(blend, 0.05)
Lr = detect(rend, 0.05)
assert Lb is not None and Lr is not None, 'landmark detect failed'
print('[solve] targets locked: %d/%d pts' % (len(Lb), len(Lr)))

# ---- Delaunay over the CURRENT landmarks (screen space) ----
tri = Delaunay(Lr)
print('[solve] delaunay tris:', len(tri.simplices))

# ---- per-triangle affine: current -> target (screen space) ----
affs = []
for t in tri.simplices:
    src = np.c_[Lr[t], np.ones(3)]
    dst = Lb[t]
    M, *_ = np.linalg.lstsq(src, dst, rcond=None)      # 3x2: dst = src @ M
    affs.append(M)
affs = np.array(affs)

# ---- warp the RENDER toward target on screen (diagnostic, shows the goal) ----
# dense map via per-pixel triangle lookup
h, w = rend.shape[:2]
yy, xx = np.mgrid[0:h, 0:w]
pts = np.c_[xx.ravel(), yy.ravel()].astype(np.float64)
cell = tri.find_simplex(pts)
map_x = np.zeros(h * w); map_y = np.zeros(h * w)
inside = cell >= 0
for k in np.unique(cell[inside]):
    m = affs[k]
    sel = inside & (cell == k)
    p = pts[sel]
    p1 = np.c_[p, np.ones(len(p))] @ m
    map_x[sel] = p1[:, 0]; map_y[sel] = p1[:, 1]
map_x = map_x.reshape(h, w); map_y = map_y.reshape(h, w)
target_screen = cv2.remap(rend, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_LINEAR)
cv2.imwrite(WORK + r'\relight\solve_target_screen.png', target_screen)
print('[solve] screen warp saved (this is what the 3D must look like)')

# ---- THE UNIFIED MAP, in UV/atlas space: for each mesh vertex, its UV texel
# (current) maps through the SAME screen triangle affine to a new screen pos;
# the new atlas position = current atlas pos + (screen displacement of its
# landmark triangle, converted px->texels). Texture: resample baked_full with
# the inverse displacement per texel. Geometry: displace each vertex by the
# displacement of its UV position (screen px -> mesh units, z from y, x from u).
_EA = json.load(open('D:/FL26_Mod/work/face_pipeline/uv/mesh_ea1.json'))
AV = np.asarray(_EA['vertices'], np.float64)
AU = np.asarray(_EA['uv'], np.float64)
sc_u = 800.0 / TEX                                   # atlas texel -> render px (u)
sc_v = 800.0 / TEX                                   # atlas texel -> render px (v)
vpx = AU[:, 0] % 1.0 * TEX * sc_u                    # vertex screen x (approx front proj)
vpy = (1 - AU[:, 1] % 1.0) * TEX * sc_v
vpts = np.c_[vpx, vpy]
vcell = tri.find_simplex(vpts)
vid = np.zeros((700, 2))
for i in range(700):
    k = vcell[i]
    if k < 0:
        continue
    d = (Lb[tri.simplices[k]] - Lr[tri.simplices[k]]).mean(0)   # triangle displacement (target-current)
    vid[i] = d
print('[solve] verts with displacement: %d/700' % int((np.abs(vid).sum(1) > 0.1).sum()))

# ---- texture warp: displacement field over the atlas (bilinear from verts) ----
from scipy.interpolate import LinearNDInterpolator
from scipy.ndimage import distance_transform_edt as edt
known = (np.abs(vid).sum(1) > 0.1)
interp = LinearNDInterpolator(np.c_[vpx, vpy][known], vid[known])
fallback = np.array([0.0, 0.0])
tyy, txx = np.mgrid[0:TEX, 0:TEX]
pts_a = np.c_[txx.ravel() / TEX * 800, (1 - tyy.ravel() / TEX) * 800]
disp = interp(pts_a)
nan = np.isnan(disp[:, 0])
disp[nan] = 0.0
disp = disp.reshape(TEX, TEX, 2)
# resample: new texel (x,y) takes color from (x + dx*px2tex, y + dy*px2tex)
K = TEX / 800.0
map_fx = np.clip(txx + disp[..., 0] * K, 0, TEX - 1).astype(np.float32)
map_fy = np.clip(tyy - disp[..., 1] * K, 0, TEX - 1).astype(np.float32)
bake_warp = cv2.remap(bake.astype(np.float32), map_fx, map_fy, cv2.INTER_LINEAR)
Image.fromarray(np.clip(bake_warp, 0, 255).astype(np.uint8)).save(WORK + r'\baked_solve.png')
print('[solve] baked_solve.png saved')

# ---- geometry: same displacement, converted to mesh units ----
d2 = json.load(open(WORK + r'\stage2_sculpt.json'))
SV = np.asarray(d2['vertices'], np.float64)
ux = 0.0592 / 125.0                                  # mesh units per render px
SV[:, 0] += vid[:, 0] * ux
SV[:, 2] -= vid[:, 1] * ux                            # screen y down = mesh z down
res = {'vertices': SV.tolist(), 'triangles': d2['triangles'], 'uv': d2['uv'],
       'source': 'ea1+mannequin+solve_unified',
       'disp_mean': float(np.abs(vid).mean())}
json.dump(res, open(WORK + r'\stage2_solve.json', 'w'))
print('[solve] stage2_solve.json saved (texture and geometry share the same warp)')