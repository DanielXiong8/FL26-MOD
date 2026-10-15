# -*- coding: utf-8 -*-
"""
B3/B4 v2: Cross-validate UV landmarks via TEXTURE PIXEL CONTENT.
Face textures have characteristic regions:
  - eyes: darker, lower brightness patches (roughly symmetric)
  - lips: red-shifted (R >> B)
  - skin: R > G > B dominant region
Strategy: analyze pixel statistics of face_african_new1, find eye/lip pixel
locations, then find which mesh UVs fall there -> validated landmark UVs.
"""
import sys, io, os, json, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image
import numpy as np

OUT = r'C:\FL26_Mod\work\face_pipeline\uv'

img = Image.open(os.path.join(OUT, 'face_african_new1_extracted.png')).convert('RGB')
W, H = img.size
print(f"texture: {W}x{H}")
px = np.asarray(img).astype(np.float32)  # (H, W, 3), row 0 = TOP of image = v=1
R, G, B = px[..., 0], px[..., 1], px[..., 2]

brightness = (R + G + B) / 3.0
redness = R - B  # lips / skin high
# alpha mask check (if original had alpha)
img_a = Image.open(os.path.join(OUT, 'face_african_new1_extracted.png'))
print(f"mode: {img_a.mode}")
if img_a.mode == 'RGBA':
    alpha = np.asarray(img_a)[..., 3]
    valid = alpha > 10
    print(f"alpha valid pixels: {valid.sum()} / {W*H} ({100*valid.sum()/(W*H):.1f}%)")
else:
    valid = np.ones((H, W), bool)

# ---- grid statistics: 32x32 cells ----
G_N = 32
print("\nBrightness grid (v from TOP=1.0 to BOTTOM=0.0), only cells with valid alpha:")
grid = []
for gy in range(G_N):
    row = []
    for gx in range(G_N):
        y0, y1 = gy * H // G_N, (gy + 1) * H // G_N
        x0, x1 = gx * W // G_N, (gx + 1) * W // G_N
        m = valid[y0:y1, x0:x1]
        if m.sum() < 50:
            row.append(None)
            continue
        b = brightness[y0:y1, x0:x1][m].mean()
        r = redness[y0:y1, x0:x1][m].mean()
        row.append((b, r))
    grid.append(row)

# ASCII brightness map (v=1 at top)
print("\nASCII brightness map (dark='.', mid='o', bright='#', empty=' '):")
for gy in range(G_N):
    line = ""
    for gx in range(G_N):
        c = grid[gy][gx]
        if c is None:
            line += " "
        else:
            b = c[0]
            line += '#' if b > 140 else ('o' if b > 80 else '.')
    print(f"v={1 - (gy+0.5)/G_N:.2f} |{line}|")

# ---- eye detection: darkest valid cells in upper-middle region ----
candidates = []
for gy in range(G_N):
    for gx in range(G_N):
        c = grid[gy][gx]
        if c is None:
            continue
        v_center = 1 - (gy + 0.5) / G_N
        u_center = (gx + 0.5) / G_N
        b, r = c
        candidates.append({'u': u_center, 'v': v_center, 'b': b, 'r': r, 'gx': gx, 'gy': gy})

# eyes: dark cells, upper half (v > 0.5)
dark = sorted([c for c in candidates if c['v'] > 0.45], key=lambda c: c['b'])[:12]
print("\nDarkest cells (v>0.45, eye candidates):")
for c in dark:
    print(f"  u={c['u']:.3f} v={c['v']:.3f} brightness={c['b']:.0f} redness={c['r']:.0f}")

# lips: highest redness cells below eyes
lip = sorted([c for c in candidates if c['v'] < 0.7 and c['v'] > 0.3], key=lambda c: -c['r'])[:8]
print("\nReddest cells (0.3<v<0.7, lip candidates):")
for c in lip:
    print(f"  u={c['u']:.3f} v={c['v']:.3f} brightness={c['b']:.0f} redness={c['r']:.0f}")

# ---- where do mesh UVs concentrate? density map ----
with open(os.path.join(OUT, 'mesh_uv.json')) as f:
    uvs = json.load(f)['uv']
dens = np.zeros((G_N, G_N))
for p in uvs:
    u, v = p['u'], p['v']
    if 0 <= u < 1 and 0 <= v < 1:
        gx = min(G_N - 1, int(u * G_N))
        gy = min(G_N - 1, int((1 - v) * G_N))
        dens[gy, gx] += 1
print("\nMesh UV density map (verts per cell):")
for gy in range(G_N):
    line = ""
    for gx in range(G_N):
        d = dens[gy, gx]
        line += '#' if d > 10 else ('+' if d > 3 else ('.' if d > 0 else ' '))
    print(f"v={1 - (gy+0.5)/G_N:.2f} |{line}|")

# save analysis
out = {
    'eye_candidates': dark,
    'lip_candidates': lip,
    'density': dens.tolist(),
}
with open(os.path.join(OUT, 'texture_analysis.json'), 'w') as f:
    json.dump(out, f, indent=2)
print("\nSaved texture_analysis.json")
