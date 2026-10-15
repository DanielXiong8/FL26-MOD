# -*- coding: utf-8 -*-
# track_d_bake3.py - two-stage alignment: coarse similarity -> MP re-detect on warped photo -> dense TPS refine
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image

WORK = r'C:\FL26_Mod\work\face_pipeline\track_d'
UV_DIR = r'C:\FL26_Mod\work\face_pipeline\uv'
TEX = 512
m = json.load(open(os.path.join(UV_DIR, 'mesh_se3.json')))
V = np.array(m['vertices'], np.float32)
U = np.array(m['uv'], np.float32)
TRI = np.array([[t[0][0], t[1][0], t[2][0]] for t in m['triangles']], np.int64)
v0, v1, v2 = V[TRI[:,0]], V[TRI[:,1]], V[TRI[:,2]]
FN = np.cross(v1-v0, v2-v0); FN /= (np.linalg.norm(FN,axis=1,keepdims=True)+1e-9)
front_t = np.where(FN[:,2] > 0.4)[0]
bake_t  = np.where(FN[:,2] > 0.55)[0]

base = np.array(Image.open(os.path.join(WORK,'baseline_southeuropean_new3.png')).convert('RGB'))

FX0,FX1,FY0,FY1,RS = -0.10,0.10,-0.125,0.125,1024
def mesh2render(p): return np.stack([(p[:,0]-FX0)/(FX1-FX0)*RS, (1-(p[:,1]-FY0)/(FY1-FY0))*RS],1)
def render2mesh(p): return np.stack([p[:,0]/RS*(FX1-FX0)+FX0, (1-p[:,1]/RS)*(FY1-FY0)+FY0],1)

# ---------- render front view (for detection only) ----------
tex_px = np.stack([U[:,0]*TEX, (1-U[:,1])*TEX],1)
rend = np.zeros((RS,RS,3), np.uint8)
for ti in front_t:
    a,b,c = TRI[ti]
    q = mesh2render(V[[a,b,c]][:,:2]); t = tex_px[[a,b,c]]
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
    rend[ys[ins].astype(int), xs[ins].astype(int)] = base[py[ins], px[ins]]

# ---------- MP utils ----------
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
model = os.path.join(UV_DIR,'..','face_landmarker_v2_with_blendshapes.task')
def detect(bgr, loose=False):
    h,w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=model),
        running_mode=vision.RunningMode.IMAGE, num_faces=5 if loose else 1,
        min_face_detection_confidence=0.1 if loose else 0.5)
    mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with vision.FaceLandmarker.create_from_options(opts) as l: r = l.detect(mpi)
    if not r.face_landmarks: return None
    return np.array([[p.x*w,p.y*h] for p in r.face_landmarks[0]], np.float32)

rend_bgr = np.ascontiguousarray(rend[...,::-1])
lmR_all = detect(rend_bgr, loose=True)
lmR_all = [] if lmR_all is None else [lmR_all] if lmR_all.ndim==2 else list(lmR_all)
if not any(len(f)>=468 for f in lmR_all):
    # fallback: save + enhance + retry
    cv2.imwrite(os.path.join(WORK,'_rend_tmp.png'), rend_bgr)
    img2 = cv2.imread(os.path.join(WORK,'_rend_tmp.png'))
    for prep in [img2,
                 cv2.convertScaleAbs(img2, alpha=1.4, beta=20),
                 cv2.GaussianBlur(img2,(5,5),0),
                 cv2.resize(img2,(512,512)),
                 cv2.flip(img2,1)]:
        r = detect(prep, loose=True)
        if r is None: continue
        lmR_all = [r] if r.ndim==2 else list(r)
        if any(len(f)>=468 for f in lmR_all): break
# pick most plausible: upright face, eyes above nose, chin below
def plausible(L):
    if len(L) < 468: return 1e9
    e0,e1,n,c,f = L[159],L[386],L[1],L[199],L[10]
    if not (f[1]<e0[1]<n[1]<c[1]): return 1e9
    return abs((e0[0]+e1[0])/2 - ((f[0]+c[0])/2))/RS
lmR = min([f for f in lmR_all if len(f)>=468] or [np.zeros((1,2),np.float32)], key=plausible)
def plausible(L):
    if len(L) < 468: return 1e9
    e0,e1,n,c,f = L[159],L[386],L[1],L[199],L[10]
    if not (f[1]<e0[1]<n[1]<c[1]): return 1e9
    return abs((e0[0]+e1[0])/2 - ((f[0]+c[0])/2))/RS
lmR = min(lmR_all, key=plausible)
photo = cv2.imread(os.path.join(WORK,'photo_111.png'))
lmP = detect(photo)
print("render faces:", len(lmR_all), "full:", len(lmR), "photo ok:", lmP is not None)
if len(lmR) < 468: print("FAIL: no full render face"); sys.exit(1)

# ---------- stage 1: coarse similarity photo -> render ----------
M0,_ = cv2.estimateAffinePartial2D(lmP, lmR, method=cv2.RANSAC, ransacReprojThreshold=10)
print("M0:\n", M0.round(4))
img1 = cv2.warpAffine(photo, M0, (RS,RS), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(img1[...,::-1]).save(os.path.join(WORK,'stage1_coarse.png'))
lm1 = detect(img1)
if lm1 is None:
    print("FAIL: MP cannot re-detect on warped photo"); sys.exit(1)
print("stage1 re-detected:", len(lm1))

# ---------- stage 2: dense TPS img1 -> render ----------
S, D = lm1, lmR
rbf_x = Rbf_x = None
from scipy.interpolate import Rbf
rbf_x = Rbf(D[:,0], D[:,1], S[:,0], function='thin_plate', smooth=2.0)
rbf_y = Rbf(D[:,0], D[:,1], S[:,1], function='thin_plate', smooth=2.0)
res = np.hypot(rbf_x(D[:,0],D[:,1])-S[:,0], rbf_y(D[:,0],D[:,1])-S[:,1])
print("stage2 TPS residual mean %.2f px (of %d)" % (res.mean(), len(S)))
def render_to_img1(px):
    return np.stack([rbf_x(px[...,0],px[...,1]), rbf_y(px[...,0],px[...,1])], -1)

# ---------- bake: texel -> mesh xy -> render px -> img1 px ----------
out = base.copy()
mask = np.zeros((TEX,TEX), np.float32)
h,w = photo.shape[:2]
for ti in bake_t:
    a,b,c = TRI[ti]
    p = tex_px[[a,b,c]] if False else np.stack([U[[a,b,c],0]*TEX,(1-U[[a,b,c],1])*TEX],1)
    q = V[[a,b,c]][:,:2]
    xmin,xmax = max(int(p[:,0].min()),0), min(int(p[:,0].max())+1,TEX-1)
    ymin,ymax = max(int(p[:,1].min()),0), min(int(p[:,1].max())+1,TEX-1)
    if xmax<xmin or ymax<ymin: continue
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
    ipx = render_to_img1(rpx).reshape(len(xs),len(xs[0]),2) if xs.ndim==2 else None
    pw,ph = ipx[...,0], ipx[...,1]
    valid = ins & (pw>=0)&(pw<RS-1)&(ph>=0)&(ph<RS-1)
    if not valid.any(): continue
    px = np.clip(pw,0,RS-1).astype(int); py = np.clip(ph,0,RS-1).astype(int)
    yy,xx = ys[valid].astype(int), xs[valid].astype(int)
    out[yy,xx] = img1[py[valid], px[valid]][..., ::-1]
    mask[yy,xx] = 1

out[mask>0]=[255,0,255]
print("baked %d px (%.1f%%)" % (int(mask.sum()), mask.mean()*100))
diff = np.abs(out.astype(float)-base.astype(float)).mean()
print("mean diff vs baseline: %.1f" % diff)
Image.fromarray(out).save(os.path.join(WORK,'baked_v4_magenta.png'))
# diagnostics: where did the photo eyes/mouth land in texture?
for name, lmi in [('eyeL',159),('eyeR',386),('nose',1),('mouth',13)]:
    rpx = lmR[lmi][None]
    ipx = render_to_img1(rpx)[0]
    mxy = render2mesh(rpx)[0]
    print(f"{name}: render {rpx[0].round(0)} -> photo-px {ipx.round(1)} | mesh xy {mxy.round(3)}")
print("done -> baked_v4_magenta.png")
