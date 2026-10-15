# -*- coding: utf-8 -*-
# track_d_bake5.py - bake photo using EMPIRICAL mesh_xy -> game-UV mapping from gradient probe
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image
from scipy.interpolate import Rbf

WORK = r'C:\FL26_Mod\work\face_pipeline\track_d'
UV_DIR = r'C:\FL26_Mod\work\face_pipeline\uv'
TEX = 512
m = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
V = np.array(m['vertices'], np.float32)
U = np.array(m['uv'], np.float32)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
v0, v1, v2 = V[TRI[:,0]], V[TRI[:,1]], V[TRI[:,2]]
FN = np.cross(v1-v0, v2-v0); FN /= (np.linalg.norm(FN,axis=1,keepdims=True)+1e-9)
front_t = np.where(FN[:,2] > 0.4)[0]
bake_t  = np.where(FN[:,2] > 0.55)[0]
# render+alignment reference mesh: southeuropean (MP-detectable), same coordinate convention
mse = json.load(open(os.path.join(UV_DIR, 'mesh_se3.json')))
Vse = np.array(mse['vertices'], np.float32); Use = np.array(mse['uv'], np.float32)
TRIse = np.array([[t[0][0], t[1][0], t[2][0]] for t in mse['triangles']], np.int64)
v0s,v1s,v2s = Vse[TRIse[:,0]], Vse[TRIse[:,1]], Vse[TRIse[:,2]]
FNse = np.cross(v1s-v0s, v2s-v0s); FNse /= (np.linalg.norm(FNse,axis=1,keepdims=True)+1e-9)
se_front = np.where(FNse[:,2] > 0.4)[0]

base = np.array(Image.open(os.path.join(WORK,'baseline_eastasia_new1.png')).convert('RGB'))
base_se = np.array(Image.open(os.path.join(WORK,'baseline_southeuropean_new3.png')).convert('RGB'))
photo = cv2.imread(os.path.join(WORK,'photo_111.png'))
h, w = photo.shape[:2]

FX0,FX1,FY0,FY1,RS = -0.10,0.10,-0.125,0.125,1024
def mesh2render(p): return np.stack([(p[:,0]-FX0)/(FX1-FX0)*RS, (1-(p[:,1]-FY0)/(FY1-FY0))*RS],1)
def render2mesh(p): return np.stack([p[:,0]/RS*(FX1-FX0)+FX0, (1-p[:,1]/RS)*(FY1-FY0)+FY0],1)

# ---------- stage A: photo -> render space alignment (same as bake3, validated) ----------
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
model = os.path.join(UV_DIR,'..','face_landmarker_v2_with_blendshapes.task')
def detect(bgr, loose=False):
    hh,ww = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.IMAGE, num_faces=5 if loose else 1,
        min_face_detection_confidence=0.1 if loose else 0.5)
    mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with vision.FaceLandmarker.create_from_options(opts) as l: r = l.detect(mpi)
    if not r.face_landmarks: return None
    return np.array([[p.x*ww,p.y*hh] for p in r.face_landmarks[0]], np.float32)

def plausible(L):
    if len(L) < 468: return 1e9
    e0,e1,n,c,f = L[159],L[386],L[1],L[199],L[10]
    if not (f[1]<e0[1]<n[1]<c[1]): return 1e9
    return abs((e0[0]+e1[0])/2 - ((f[0]+c[0])/2))/RS

# render front view for detection
tex_px_se = np.stack([Use[:,0]*TEX, (1-Use[:,1])*TEX],1)
rend = np.zeros((RS,RS,3), np.uint8)
for ti in se_front:
    a,b,c = TRIse[ti]
    q = mesh2render(Vse[[a,b,c]][:,:2]); t = tex_px_se[[a,b,c]]
    xmin,xmax = int(min(q[:,0]))-1, int(max(q[:,0]))+2
    ymin,ymax = int(min(q[:,1]))-1, int(max(q[:,1]))+2
    xs,ys = np.meshgrid(np.arange(max(xmin,0),min(xmax,RS))+0.5, np.arange(max(ymin,0),min(ymax,RS))+0.5)
    d = (q[1,1]-q[2,1])*(q[0,0]-q[2,0]) + (q[2,0]-q[1,0])*(q[0,1]-q[2,1])
    if abs(d)<1e-9: continue
    w0 = ((q[1,1]-q[2,1])*(xs-q[2,0]) + (q[2,0]-q[1,0])*(ys-q[2,1]))/d
    w1 = ((q[2,1]-q[0,1])*(xs-q[2,0]) + (q[0,0]-q[2,0])*(ys-q[2,1]))/d
    w2 = 1-w0-w1
    ins = (w0>=-1e-3)&(w1>=-1e-3)&(w2>=-1e-3)
    if not ins.any(): continue
    tu = w0[...,None]*t[0] + w1[...,None]*t[1] + w2[...,None]*t[2]
    px = np.clip(tu[...,0],0,TEX-1).astype(int); py = np.clip(tu[...,1],0,TEX-1).astype(int)
    rend[ys[ins].astype(int), xs[ins].astype(int)] = base_se[py[ins], px[ins]]

rend_bgr = np.ascontiguousarray(rend[...,::-1])
lmR = detect(rend_bgr, loose=True)
if lmR is None or len(lmR) < 468:
    cv2.imwrite(os.path.join(WORK,'_rend6_tmp.png'), rend_bgr)
    img2 = cv2.imread(os.path.join(WORK,'_rend6_tmp.png'))
    for prep in [img2, cv2.convertScaleAbs(img2, alpha=1.4, beta=20),
                 cv2.GaussianBlur(img2,(5,5),0), cv2.resize(img2,(512,512)), cv2.flip(img2,1)]:
        r = detect(prep, loose=True)
        if r is not None and len(r) >= 468: lmR = r; break
if lmR is None or len(lmR) < 468: print('FAIL render face'); sys.exit(1)
lmP = detect(photo)
if lmP is None: print('FAIL photo face'); sys.exit(1)
M0,_ = cv2.estimateAffinePartial2D(lmP, lmR, method=cv2.RANSAC, ransacReprojThreshold=10)
img1 = cv2.warpAffine(photo, M0, (RS,RS), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(img1[...,::-1]).save(os.path.join(WORK,'stage1_coarse.png'))
lm1 = detect(img1)
if lm1 is None: print('FAIL stage1 redetect'); sys.exit(1)
S, D = lm1, lmR
rbf_x = Rbf(D[:,0], D[:,1], S[:,0], function='thin_plate', smooth=2.0)
rbf_y = Rbf(D[:,0], D[:,1], S[:,1], function='thin_plate', smooth=2.0)
res = np.hypot(rbf_x(D[:,0],D[:,1])-S[:,0], rbf_y(D[:,0],D[:,1])-S[:,1])
print('photo->render TPS residual %.2f px' % res.mean())
def render_to_img1(px):
    return np.stack([rbf_x(px[...,0],px[...,1]), rbf_y(px[...,0],px[...,1])], -1)

# ---------- stage B: EMPIRICAL mesh_xy -> game UV (from gradient probe) ----------
# mesh anchors
i_nose = int(np.argmax(V[:,2])); nose_xy = V[i_nose,:2]
i_chin = int(np.argmin(V[:,1])); chin_xy = V[i_chin,:2]
band = V[:,2] > 0.05
i_cl = np.where(band)[0][np.argmin(V[band][:,0])]; cheekL_xy = V[i_cl,:2]
i_cr = np.where(band)[0][np.argmax(V[band][:,0])]; cheekR_xy = V[i_cr,:2]
# render-landmark-derived anchors (from validated detection)
eyeL_xy = render2mesh(np.array([[484.,359.]]))[0]
eyeR_xy = render2mesh(np.array([[743.,379.]]))[0]
mouth_xy = render2mesh(np.array([[557.,629.]]))[0]
forehead_xy = render2mesh(np.array([[660.,260.]]))[0]

mesh_pts = np.array([nose_xy, chin_xy, cheekL_xy, cheekR_xy, eyeL_xy, eyeR_xy, mouth_xy, forehead_xy], np.float32)
game_uv  = np.array([[0.51,0.45],[0.50,0.78],[0.24,0.47],[0.76,0.46],
                     [0.35,0.38],[0.67,0.37],[0.50,0.60],[0.52,0.24]], np.float32)
# separable empirical mapping: u = c + a*x (linear), v = PCHIP(y) (monotone 1D)
from scipy.interpolate import PchipInterpolator
ux = np.array([[-0.10,0.14],[-0.078,0.24],[0.0,0.51],[0.078,0.76],[0.10,0.88]])
A = np.stack([np.ones(len(ux)), ux[:,0]],1)
coef, *_ = np.linalg.lstsq(A, ux[:,1], rcond=None)
print('u(x) = %.3f + %.3f*x' % (coef[0], coef[1]))
vy = PchipInterpolator([-0.125,-0.108,-0.029,0.010,0.035,0.0615,0.109],
                       [0.85, 0.78, 0.60, 0.45, 0.375, 0.24, 0.15])
def map_uv(pts):
    return np.stack([coef[0] + coef[1]*pts[:,0], vy(np.clip(pts[:,1],-0.125,0.109))],1)
pred = map_uv(mesh_pts)
err = np.abs(pred - game_uv).max(axis=1)
print('separable mapping max err %.4f per-anchor:' % err.max())
for nm, pr, gv in zip(['nose','chin','chL','chR','eyeL','eyeR','mouth','fhead'], pred, game_uv):
    print('  %-5s pred(%.2f,%.2f) vs probe(%.2f,%.2f)' % (nm, *pr, *gv))

# ---------- bake: triangle raster in GAME-UV texel space, sample via mesh_xy chain ----------
out = base.copy()
mask = np.zeros((TEX,TEX), np.float32)  # stores nz priority
for ti in bake_t:
    a,b,c = TRI[ti]
    q = V[[a,b,c]][:,:2]                                   # mesh xy
    gu = map_uv(q)                                          # game uv (separable empirical)
    p = np.stack([gu[:,0]*TEX, (1-gu[:,1])*TEX],1)         # game texel (v flipped: game v0=top)
    xmin,xmax = max(int(p[:,0].min()),0), min(int(p[:,0].max())+1,TEX-1)
    ymin,ymax = max(int(p[:,1].min()),0), min(int(p[:,1].max())+1,TEX-1)
    if xmax<=xmin or ymax<=ymin: continue
    xs,ys = np.meshgrid(np.arange(xmin,xmax)+0.5, np.arange(ymin,ymax)+0.5)
    d = (p[1,1]-p[2,1])*(p[0,0]-p[2,0]) + (p[2,0]-p[1,0])*(p[0,1]-p[2,1])
    if abs(d)<1e-9: continue
    w0 = ((p[1,1]-p[2,1])*(xs-p[2,0]) + (p[2,0]-p[1,0])*(ys-p[2,1]))/d
    w1 = ((p[2,1]-p[0,1])*(xs-p[2,0]) + (p[0,0]-p[2,0])*(ys-p[2,1]))/d
    w2 = 1-w0-w1
    ins = (w0>=-1e-3)&(w1>=-1e-3)&(w2>=-1e-3)
    if not ins.any(): continue
    xy = w0[...,None]*q[0] + w1[...,None]*q[1] + w2[...,None]*q[2]
    rpx = mesh2render(xy.reshape(-1,2))
    ipx = render_to_img1(rpx).reshape(*xs.shape, 2)
    pw, ph = ipx[...,0], ipx[...,1]
    valid = ins & (pw>=0)&(pw<RS-1)&(ph>=0)&(ph<RS-1)
    if not valid.any(): continue
    px = np.clip(pw,0,RS-1).astype(int); py = np.clip(ph,0,RS-1).astype(int)
    yy,xx = ys[valid].astype(int), xs[valid].astype(int)
    nz = FN[ti,2]
    take = nz >= mask[yy,xx]
    out[yy[take],xx[take]] = img1[py[valid][take], px[valid][take]][..., ::-1]
    mask[yy[take],xx[take]] = nz

print('baked %d px (%.1f%%)' % (int(mask.sum()), mask.mean()*100))
print('mean diff vs baseline: %.1f' % np.abs(out.astype(float)-base.astype(float)).mean())
Image.fromarray(out).save(os.path.join(WORK,'baked_ea1.png'))
print('done -> baked_ea1.png')
