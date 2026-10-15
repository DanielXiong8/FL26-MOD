# -*- coding: utf-8 -*-
"""
Track C prototype: Photo -> FL26 face texture (512x512 RGBA).

Pipeline:
  photo.jpg -> face landmarks (src, photo pixel coords)
            -> Piecewise-Affine warp (Delaunay triangulation on FL26 UV targets)
            -> 512x512 FL26 UV-space texture
            -> Poisson-blend onto base template for ears/neck coverage

Self-test mode (--selftest): no real photo needed.
  Simulates a "photo" by applying a known affine transform to the FL26 texture
  face region, then checks the pipeline recovers the original texture.
  Metric: PSNR on face region (u 0.15-0.85, v 0.35-0.87).
"""
import sys, io, os, json, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import numpy as np
import cv2
from PIL import Image
from scipy.spatial import Delaunay

OUT_UV = r'C:\FL26_Mod\work\face_pipeline\uv'
OUT_GEN = r'C:\FL26_Mod\work\face_pipeline\generated'
os.makedirs(OUT_GEN, exist_ok=True)

TEX_SIZE = 512

# ---------------- landmark loading ----------------
def load_fl26_landmarks():
    """returns dict name -> (u, v) in [0,1]"""
    with open(os.path.join(OUT_UV, 'uv_landmark_map.json')) as f:
        d = json.load(f)
    return {k: tuple(v['uv']) for k, v in d['landmarks'].items()}

# ---------------- piecewise affine warp ----------------
def warp_piecewise_affine(src_img, src_pts, dst_pts, out_size):
    """src_img -> warped to out_size, mapping src_pts to dst_pts.
    src_pts, dst_pts: (N,2) float32 arrays in PIXEL coordinates."""
    src_pts = np.asarray(src_pts, np.float32)
    dst_pts = np.asarray(dst_pts, np.float32)

    # add stable boundary anchors (identity-ish frame)
    H, W = src_img.shape[:2]
    src_frame = np.array([[0,0],[W-1,0],[W-1,H-1],[0,H-1],[W/2,0],[W/2,H-1],[0,H/2],[W-1,H/2]], np.float32)
    # map frame points via global affine fit of the landmark correspondences
    A = estimate_affine(src_pts, dst_pts)
    dst_frame = apply_affine(src_frame, A)

    all_src = np.vstack([src_pts, src_frame])
    all_dst = np.vstack([dst_pts, dst_frame])

    tri = Delaunay(all_dst)
    out = np.zeros((out_size, out_size, src_img.shape[2] if src_img.ndim == 3 else 3), np.uint8)

    for simplex in tri.simplices:
        d = all_dst[simplex].astype(np.float32)
        s = all_src[simplex].astype(np.float32)
        rect_d = cv2.boundingRect(d)
        x, y, w, h = rect_d
        # clamp to out image bounds
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(out_size, x + w)
        y1 = min(out_size, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        d_crop = d - [x0, y0]
        mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillConvexPoly(mask, np.int32(d_crop), 255)
        M = cv2.getAffineTransform(s, d)
        # adjust M for cropped origin (x0, y0)
        M_crop = M.copy()
        M_crop[0, 2] -= x0
        M_crop[1, 2] -= y0
        warped = cv2.warpAffine(src_img, M_crop, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        roi = out[y0:y1, x0:x1]
        m = mask > 0
        roi[m] = warped[m]
    return out

def estimate_affine(src, dst):
    M, _ = cv2.estimateAffinePartial2D(src, dst)
    if M is None:
        M = np.array([[1,0,0],[0,1,0]], np.float32)
    return M

def apply_affine(pts, M):
    pts_h = np.hstack([pts, np.ones((len(pts), 1), np.float32)])
    return (M @ pts_h.T).T

# ---------------- main: selftest ----------------
def selftest():
    fl26 = load_fl26_landmarks()
    base_tex = np.array(Image.open(os.path.join(OUT_UV, 'face_african_new1_extracted.png')).convert('RGB'))
    print(f"base texture: {base_tex.shape}")

    # FL26 UV landmark targets in texture pixel space
    dst_uv = {k: (u * TEX_SIZE, (1 - v) * TEX_SIZE) for k, (u, v) in fl26.items()}  # v flipped: image row 0 = v=1

    # --- simulate a photo: affine transform of UV space into a 640x640 "photo frame"
    # photo = texture region transformed; src landmarks = transformed uv points
    angle = math.radians(-8)
    scale = 420.0  # face spans ~420px in photo
    tx, ty = 320.0, 300.0  # photo center
    A_sim = np.array([
        [scale * math.cos(angle), -scale * math.sin(angle), tx],
        [scale * math.sin(angle),  scale * math.cos(angle), ty],
    ], np.float32)
    # uv pts (u right, v up) -> photo pts (x right, y DOWN): flip v
    uv_pts = np.array([[u, 1 - v] for u, v in fl26.values()], np.float32)
    src_photo_pts = apply_affine(uv_pts, A_sim)

    # mock photo image = warp texture by A_sim into 640x640
    photo = cv2.warpAffine(base_tex, A_sim, (640, 640), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    cv2.imwrite(os.path.join(OUT_GEN, 'mock_photo.png'), cv2.cvtColor(photo, cv2.COLOR_RGB2BGR))

    # --- run the real pipeline: photo landmarks -> FL26 UV space
    dst_pts = np.array([dst_uv[k] for k in fl26.keys()], np.float32)
    warped = warp_piecewise_affine(photo, src_photo_pts, dst_pts, TEX_SIZE)
    Image.fromarray(warped).save(os.path.join(OUT_GEN, 'custom_face_test.png'))
    print("custom_face_test.png written")

    # --- metric: PSNR vs original texture in face region
    u0, u1 = int(0.15 * TEX_SIZE), int(0.85 * TEX_SIZE)
    v0, v1 = int((1 - 0.87) * TEX_SIZE), int((1 - 0.35) * TEX_SIZE)  # image y
    a = base_tex[v0:v1, u0:u1].astype(np.float32)
    b = warped[v0:v1, u0:u1].astype(np.float32)
    mse = ((a - b) ** 2).mean()
    psnr = 10 * math.log10(255 * 255 / mse) if mse > 0 else 99.0
    print(f"SELFTEST PSNR (face region): {psnr:.2f} dB  (mse={mse:.1f})")
    print("  >30dB = good recovery, >25dB = acceptable for structure-correct prototype")

    # side-by-side comparison image
    cmp = np.hstack([base_tex, warped])
    Image.fromarray(cmp).save(os.path.join(OUT_GEN, 'selftest_compare.png'))
    print("selftest_compare.png written (left=original, right=pipeline output)")

if __name__ == '__main__':
    selftest()
