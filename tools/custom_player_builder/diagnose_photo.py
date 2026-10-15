# -*- coding: utf-8 -*-
"""Diagnose face detection on 111.jpg"""
import sys, io, os, cv2, numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import mediapipe as mp

PHOTO = r'C:\Users\Lenovo\OneDrive\Desktop\111.jpg'
MODEL = r'C:\FL26_Mod\work\face_pipeline\face_landmarker_v2_with_blendshapes.task'

img = cv2.imread(PHOTO)
print("img shape:", img.shape if img is not None else "None")
if img is None:
    print("FAIL: cv2 couldn't read image")
    sys.exit(1)
h, w = img.shape[:2]
print("mean brightness:", img.mean())

# try multiple scales
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.IMAGE,
    num_faces=1,
)
landmarker = vision.FaceLandmarker.create_from_options(options)

for scale, label in [(1.0, 'orig'), (2.0, '2x'), (0.5, 'half')]:
    resized = cv2.resize(img, (int(w*scale), int(h*scale)))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    mpimg = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = landmarker.detect(mpimg)
    n = len(res.face_landmarks)
    print(f"scale {label} ({resized.shape[1]}x{resized.shape[0]}): {n} faces")
    if n > 0:
        print("  face found!")
        # save a copy with the face box drawn using landmarks extremes
        lm = res.face_landmarks[0]
        xs = [p.x for p in lm]; ys = [p.y for p in lm]
        print(f"  bbox: x[{min(xs):.2f},{max(xs):.2f}] y[{min(ys):.2f},{max(ys):.2f}]")
        break
landmarker.close()

# Also check if there's an EXIF orientation issue - re-save rotated variants
import PIL.Image
pil = PIL.Image.open(PHOTO)
print("PIL size:", pil.size, "mode:", pil.mode)
print("EXIF:", pil.getexif().get(274, 'none'))
