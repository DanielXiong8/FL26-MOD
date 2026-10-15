# -*- coding: utf-8 -*-
# track_d_bake2.py - render front view -> MediaPipe auto-align -> per-triangle bake
# Fixes all three issues: silver face / double nose / bent brows
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

WORK = r'C:\FL26_Mod\work\face_pipeline\track_d'
UV_DIR = r'C:\FL26_Mod\work\face_pipeline\uv'
TEX = 512
TARGET = "assets/models/player2021/textures/face/face_southeuropean_new3.png"

m = json.load(open(os.path.join(UV_DIR, 'mesh_se3.json')))
V = np.array(m['vertices'], np.float32)
U = np.array(m['uv'], np.float32)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
TRI_UV = np.array([[t[0][1], t[1][1], t[2][1]] for t in m['triangles']], np.int64)
# normals
v0, v1, v2 = V[TRI[:,0]], V[TRI[:,1]], V[TRI[:,2]]
FN = np.cross(v1-v0, v2-v0)
FN /= (np.linalg.norm(FN, axis=1, keepdims=True) + 1e-9)
front_t = np.where(FN[:,2] > 0.4)[0]   # for render + landmark detection
bake_t = np.where(FN[:,2] > 0.55)[0]   # tighter islands for baking (exclude ears/jaw)
print(f"front tris: {len(front_t)}/{len(TRI)}")

base = np.array(Image.open(os.path.join(WORK, 'baseline_southeuropean_new3.png')).convert('RGB'))

# ---------- render front view ----------
FX0, FX1 = -0.10, 0.10
FY0, FY1 = -0.125, 0.125
RS = 1024  # render size
def mesh2render(pts):
    return np.stack([(pts[:,0]-FX0)/(FX1-FX0)*RS, (1-(pts[:,1]-FY0)/(FY1-FY0))*RS], 1)
def render2mesh(px):
    return np.stack([px[:,0]/RS*(FX1-FX0)+FX0, (1-px[:,1]/RS)*(FY1-FY0)+FY0], 1)

front_v = np.unique(TRI[front_t].ravel())
tex_px = np.stack([U[:,0]*TEX, (1-U[:,1])*TEX], 1)
rend = np.zeros((RS,RS,3), np.uint8)
rend_mask = np.zeros((RS,RS), np.float32)
for ti in front_t:
    a,b,c = TRI[ti]
    q0,q1,q2 = mesh2render(V[[a,b,c]])
    t0,t1,t2 = tex_px[[a,b,c]]
    xmin,xmax = int(min(q0[0],q1[0],q2[0])), int(max(q0[0],q1[0],q2[0]))+1
    ymin,ymax = int(min(q0[1],q1[1],q2[1])), int(max(q0[1],q1[1],q2[1]))+1
    xs,ys = np.meshgrid(np.arange(xmin,xmax)+0.5, np.arange(ymin,ymax)+0.5)
    d = (q1[1]-q2[1])*(q0[0]-q2[0]) + (q2[0]-q1[0])*(q0[1]-q2[1])
    if abs(d) < 1e-9: continue
    w0 = ((q1[1]-q2[1])*(xs-q2[0]) + (q2[0]-q1[0])*(ys-q2[1]))/d
    w1 = ((q2[1]-q0[1])*(xs-q2[0]) + (q0[0]-q2[0])*(ys-q2[1]))/d
    w2 = 1-w0-w1
    inside = (w0>=-1e-3)&(w1>=-1e-3)&(w2>=-1e-3)
    if not inside.any(): continue
    tu = w0[...,None]*t0 + w1[...,None]*t1 + w2[...,None]*t2
    px = np.clip(tu[...,0],0,TEX-1).astype(int); py = np.clip(tu[...,1],0,TEX-1).astype(int)
    yy,xx = ys[inside].astype(int), xs[inside].astype(int)
    rend[yy,xx] = base[py[inside], px[inside]]
    rend_mask[yy,xx] = 1.0
Image.fromarray(rend).save(os.path.join(WORK,'front_view_baseline.png'))
print("front view rendered, coverage %.1f%%" % (rend_mask.mean()*100))

# ---------- MediaPipe on both images ----------
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
model = os.path.join(UV_DIR, '..', 'face_landmarker_v2_with_blendshapes.task')
def detect(img_bgr):
    h,w = img_bgr.shape[:2]
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.IMAGE, num_faces=5, min_face_detection_confidence=0.1)
    mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with vision.FaceLandmarker.create_from_options(opts) as l:
        r = l.detect(mpi)
    if not r.face_landmarks: return None
    return [np.array([[p.x*w, p.y*h] for p in fl], np.float32) for fl in r.face_landmarks]

lm_rend_all = detect(np.ascontiguousarray(rend[..., ::-1]))  # rend is RGB; detect expects BGR
photo = cv2.imread(os.path.join(WORK, 'photo_111.png'))
lm_ph_list = detect(photo)
lm_ph = lm_ph_list[0]
# pick render face: eyes symmetric about x=0, eyes above nose, chin below
nose_y = 0.004
IDX = [159, 386, 1, 199, 10, 61, 291]  # eyeL, eyeR, nose, chin, forehead, mouthL, mouthR
best, best_score = None, 1e9
for fl in (lm_rend_all or []):
    px_pts = fl[IDX]
    mpts = render2mesh(px_pts)
    ex, ey = mpts[0], mpts[1]
    score = abs(ex[0]+ex[1])/2 + abs(ey[0]+ey[1])/2
    ok = (ey[0] > nose_y) and (ey[1] > nose_y) and mpts[3][1] < nose_y and 0.01 < (ex[1]-ex[0]) < 0.15
    if ok and score < best_score:
        best, best_score = fl, score
print("render face candidates:", len(lm_rend_all or []), "best score:", None if best is None else round(best_score,4))
if best is None:
    print("FAIL: no plausible render face"); sys.exit(1)
lm_rend = best
if lm_rend is None or lm_ph is None:
    print("FAIL: render face detected:", lm_rend is not None, "photo:", lm_ph is not None); sys.exit(1)
print("render landmarks:", len(lm_rend), "photo landmarks:", len(lm_ph))
dst_px = best[IDX]      # render pixels
src_all = lm_ph           # photo dense landmarks (478)
dst_all_px = best         # render dense landmarks (478), same semantics
print("dense correspondences:", len(src_all))

# init similarity on dense set, then refine with TPS in pixel space
M0, inliers = cv2.estimateAffinePartial2D(src_all, dst_all_px, method=cv2.RANSAC, ransacReprojThreshold=8)
print("init similarity:\n", M0.round(4), "inliers:", None if inliers is None else int(inliers.sum()))

from scipy.interpolate import Rbf
# TPS: render px -> photo px (control points in RENDER domain, evaluated at render px)
step = max(1, len(src_all)//300)
S = src_all[::step]; D = dst_all_px[::step]
rbf_x = Rbf(D[:,0], D[:,1], S[:,0], function='thin_plate', smooth=5.0)
rbf_y = Rbf(D[:,0], D[:,1], S[:,1], function='thin_plate', smooth=5.0)
res_x = rbf_x(D[:,0], D[:,1]) - S[:,0]; res_y = rbf_y(D[:,0], D[:,1]) - S[:,1]
print("TPS residual mean %.2f px (render space)" % (np.abs(np.concatenate([res_x,res_y])).mean()))

def photo_px_from_render(px):
    return np.stack([rbf_x(px[...,0], px[...,1]), rbf_y(px[...,0], px[...,1])], -1)

# ---------- bake ----------
out = base.copy()
tex_px_uv = np.stack([U[:,0]*TEX, (1-U[:,1])*TEX], 1)
mask = np.zeros((TEX,TEX), np.float32)
for ti in bake_t:
    a,b,c = TRI[ti]
    p0,p1,p2 = tex_px_uv[[a,b,c]]
    q0,q1,q2 = V[[a,b,c]][:,:2]
    xmin,xmax = max(int(min(p0[0],p1[0],p2[0])),0), min(int(max(p0[0],p1[0],p2[0]))+1,TEX-1)
    ymin,ymax = max(int(min(p0[1],p1[1],p2[1])),0), min(int(max(p0[1],p1[1],p2[1]))+1,TEX-1)
    if xmax<xmin or ymax<ymin: continue
    xs,ys = np.meshgrid(np.arange(xmin,xmax)+0.5, np.arange(ymin,ymax)+0.5)
    d = (p1[1]-p2[1])*(p0[0]-p2[0]) + (p2[0]-p1[0])*(p0[1]-p2[1])
    if abs(d)<1e-9: continue
    w0 = ((p1[1]-p2[1])*(xs-p2[0]) + (p2[0]-p1[0])*(ys-p2[1]))/d
    w1 = ((p2[1]-p0[1])*(xs-p2[0]) + (p0[0]-p2[0])*(ys-p2[1]))/d
    w2 = 1-w0-w1
    inside = (w0>=-1e-3)&(w1>=-1e-3)&(w2>=-1e-3)
    if not inside.any(): continue
    xy = w0[...,None]*q0 + w1[...,None]*q1 + w2[...,None]*q2
    # mesh xy -> render px -> photo px (TPS)
    rpx = mesh2render(xy.reshape(-1,2))
    ppx = photo_px_from_render(rpx).reshape(*xs.shape, 2)
    pw, phh = ppx[...,0], ppx[...,1]
    valid = inside & (pw>=0)&(pw<photo.shape[1]-1)&(phh>=0)&(phh<photo.shape[0]-1)
    if not valid.any(): continue
    px = np.clip(pw,0,photo.shape[1]-1).astype(int); py = np.clip(phh,0,photo.shape[0]-1).astype(int)
    yy,xx = ys[valid].astype(int), xs[valid].astype(int)
    out[yy,xx] = photo[py[valid], px[valid]][:, ::-1]
    mask[yy,xx] = 1

print("baked %d px (%.1f%%)" % (int(mask.sum()), mask.mean()*100))
Image.fromarray(out).save(os.path.join(WORK,'baked_v2.png'))
Image.fromarray(rend).save(os.path.join(WORK,'front_view_check.png'))
print("done -> baked_v2.png")
