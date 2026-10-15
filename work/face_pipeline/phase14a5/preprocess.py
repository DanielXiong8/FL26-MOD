# -*- coding: utf-8 -*-
"""preprocess.py (recon env) — photo prep for the face pipeline.
Background neutralization (strong chroma bg) + face tight-crop to 900x900.
Usage: python preprocess.py <in_photo> <out_photo>
"""
import sys, os
import numpy as np, cv2

src, dst = sys.argv[1], sys.argv[2]
img = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_COLOR)
h, w = img.shape[:2]

# 1) strong-chroma background removal (ID-photo blue etc.)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
mask = ((hsv[:, :, 0] >= 85) & (hsv[:, :, 0] <= 135) & (hsv[:, :, 1] > 60)).astype(np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
n, lbl, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
bg = np.zeros_like(mask)
for i in range(1, n):
    x, y, bw, bh, area = stats[i]
    if area > h * w * 0.02 and (x == 0 or y == 0 or x + bw >= w or y + bh >= h):
        bg[lbl == i] = 1
if bg.mean() > 0.05:
    img[bg == 1] = (128, 128, 128)
    print('bg neutralized: %.1f%%' % (100.0 * bg.mean()))

# 2) face tight-crop
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
faces = cas.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
if len(faces):
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    cx, cy = x + fw // 2, y + fh // 2
    r = int(max(fw, fh) * 1.05)
    x0, x1 = max(cx - r, 0), min(cx + r, w)
    y0, y1 = max(cy - r, 0), min(cy + r, h)
    img = img[y0:y1, x0:x1]
    print('face crop: box(%d,%d,%d,%d) -> %s' % (x, y, fw, fh, img.shape[:2]))
else:
    print('no face found, keeping full frame')
img = cv2.resize(img, (900, 900), interpolation=cv2.INTER_LANCZOS4)
ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 96]); buf.tofile(dst)
print('saved', dst)
