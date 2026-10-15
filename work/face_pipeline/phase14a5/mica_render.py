# -*- coding: utf-8 -*-
"""mica_render.py (recon env) — shaded photo-handed views of a MICA mesh.
Usage: python mica_render.py <mesh.obj> <out_dir> <sheet_title>
Outputs: mica_sheet.png + per-view pngs in out_dir.
"""
import sys, os
import numpy as np, trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

mesh_obj, OUT, title = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else 'MICA rebuild')
os.makedirs(OUT, exist_ok=True)
m = trimesh.load(mesh_obj, process=False)
V = np.asarray(m.vertices, np.float64).copy()
V[:, 0] *= -1.0                                  # photo-handed flip
F = np.asarray(m.faces, np.int64)[:, ::-1]
R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float64)
Vr = V @ R.T

# nose-driven orientation: rotate so the face's forward vector (head center ->
# kpt68 nose tip, horizontal) points at +Y, then the front camera at azim=90
# truly sees the FACE (the old fixed angles showed the back of the head).
kp = np.load(os.path.join(os.path.dirname(mesh_obj), 'kpt68.npy'))[0].copy()
kp[:, 0] *= -1.0
kp_r = kp @ R.T
fwd = kp_r[30] - kp_r.mean(0)
theta = np.arctan2(fwd[1], fwd[0])
a = -theta + np.pi / 2.0   # align forward to +Y, where the azim=90 camera sits
rot = np.array([[np.cos(a), -np.sin(a), 0],
                [np.sin(a),  np.cos(a), 0],
                [0, 0, 1]], np.float64)
Vr = Vr @ rot.T
Vr = (Vr - Vr.mean(0)) / (Vr.max(0) - Vr.min(0)).max()

def render(ax, elev, azim, t):
    tri = Vr[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    light = np.array([0.3, 0.45, 0.84]); light /= np.linalg.norm(light)
    lam = np.clip(n @ light, 0, 1) * 0.75 + 0.25
    col = np.stack([lam * 0.86, lam * 0.78, lam * 0.70, np.ones_like(lam)], 1)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolors='none'))
    ax.set_xlim(-0.45, 0.45); ax.set_ylim(-0.45, 0.45); ax.set_zlim(-0.5, 0.4)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title('%s - %s' % (title, t))
    ax.set_box_aspect((1, 1, 1))

views = [(0, 90, 'front'), (0, 50, '3_4_left'), (0, 130, '3_4_right'),
         (0, 0, 'side'), (90, 90, 'top'), (-25, 90, 'from_below')]
fig = plt.figure(figsize=(16, 11))
for k, (e, a, t) in enumerate(views):
    ax = fig.add_subplot(2, 3, k + 1, projection='3d')
    render(ax, e, a, t.replace('_', ' '))
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'mica_sheet.png'), dpi=110)
for e, a, t in views:
    f1 = plt.figure(figsize=(7, 7))
    ax = f1.add_subplot(111, projection='3d')
    render(ax, e, a, t.replace('_', ' '))
    plt.tight_layout()
    f1.savefig(os.path.join(OUT, 'mica_%s.png' % t), dpi=110)
    plt.close(f1)
# flipped mesh export for Blender viewing
m2 = trimesh.Trimesh(vertices=V, faces=F, process=False)
m2.export(os.path.join(OUT, 'mica_mesh_photo_handed.obj'))
print('mica renders saved to', OUT)
