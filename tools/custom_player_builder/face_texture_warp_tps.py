# -*- coding: utf-8 -*-
"""Try TPS warp via scipy Rbf (thin_plate_spline) vs current PWA result."""
import sys, io, os, json, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image
from scipy.interpolate import Rbf

OUT_UV = r'C:\FL26_Mod\work\face_pipeline\uv'
OUT_GEN = r'C:\FL26_Mod\work\face_pipeline\generated'
TEX_SIZE = 512

def load_fl26_landmarks():
    with open(os.path.join(OUT_UV, 'uv_landmark_map.json')) as f:
        d = json.load(f)
    return {k: tuple(v['uv']) for k, v in d['landmarks'].items()}

def apply_affine(pts, M):
    pts_h = np.hstack([pts, np.ones((len(pts), 1), np.float32)])
    return (M @ pts_h.T).T

fl26 = load_fl26_landmarks()
base_tex = np.array(Image.open(os.path.join(OUT_UV, 'face_african_new1_extracted.png')).convert('RGB'))

# same simulated photo as face_texture_warp.py selftest
angle = math.radians(-8)
scale = 420.0
tx, ty = 320.0, 300.0
A_sim = np.array([[scale*math.cos(angle), -scale*math.sin(angle), tx],
                  [scale*math.sin(angle),  scale*math.cos(angle), ty]], np.float32)
uv_pts = np.array([[u, 1 - v] for u, v in fl26.values()], np.float32)  # to image-y-down
src_photo_pts = apply_affine(uv_pts, A_sim)
photo = cv2.warpAffine(base_tex, A_sim, (640, 640), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

# dst = FL26 UV texture pixel coords
dst_pts = np.array([[u * TEX_SIZE, (1 - v) * TEX_SIZE] for u, v in fl26.values()], np.float32)

# --- TPS: build inverse map dst(pixel in texture) -> src(pixel in photo)
# Rbf per coordinate: input dst control pts, output src coords
rbf_x = Rbf(dst_pts[:, 0], dst_pts[:, 1], src_photo_pts[:, 0], function='thin_plate')
rbf_y = Rbf(dst_pts[:, 0], dst_pts[:, 1], src_photo_pts[:, 1], function='thin_plate')

# query grid (only evaluate inside landmark convex hull + margin; outside -> replicate border)
gy, gx = np.mgrid[0:TEX_SIZE, 0:TEX_SIZE].astype(np.float32)
map_x = rbf_x(gx.ravel(), gy.ravel()).reshape(TEX_SIZE, TEX_SIZE).astype(np.float32)
map_y = rbf_y(gx.ravel(), gy.ravel()).reshape(TEX_SIZE, TEX_SIZE).astype(np.float32)

warped = cv2.remap(photo, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
Image.fromarray(warped).save(os.path.join(OUT_GEN, 'custom_face_test_tps.png'))

u0, u1 = int(0.15*TEX_SIZE), int(0.85*TEX_SIZE)
v0, v1 = int((1-0.87)*TEX_SIZE), int((1-0.35)*TEX_SIZE)
a = base_tex[v0:v1, u0:u1].astype(np.float32)
b = warped[v0:v1, u0:u1].astype(np.float32)
mse = ((a-b)**2).mean()
psnr = 10*math.log10(255*255/mse) if mse > 0 else 99.0
print(f"TPS SELFTEST PSNR (face region): {psnr:.2f} dB (mse={mse:.1f})  [PWA baseline: 24.39 dB]")

cmp = np.hstack([base_tex, warped])
Image.fromarray(cmp).save(os.path.join(OUT_GEN, 'selftest_compare_tps.png'))
print("custom_face_test_tps.png / selftest_compare_tps.png written")
