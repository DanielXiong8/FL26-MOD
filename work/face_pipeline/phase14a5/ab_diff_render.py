# -*- coding: utf-8 -*-
import numpy as np, trimesh, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

A = r'D:\FL26_Mod\work\face_pipeline\regression\set2_1jpg\mica_mesh\mica\mesh.obj'
B = r'D:\FL26_Mod\work\face_pipeline\regression\set4_idphoto\mica_mesh\mica\mesh.obj'
OUT = r'D:\FL26_Mod\work\face_pipeline\regression'
def load_flip(p):
    m = trimesh.load(p, process=False)
    V = np.asarray(m.vertices, np.float64).copy(); V[:, 0] *= -1.0
    F = np.asarray(m.faces, np.int64)[:, ::-1]
    return V, F
VA, FA = load_flip(A)
VB, FB = load_flip(B)
R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], np.float64)
VA_r, VB_r = VA @ R.T, VB @ R.T
kp = np.load(r'D:\FL26_Mod\work\face_pipeline\regression\set4_idphoto\mica_mesh\mica\kpt68.npy')[0].copy()
kp[:, 0] *= -1; kp_r = kp @ R.T
fwd = kp_r[30] - kp_r.mean(0)
theta = np.arctan2(fwd[1], fwd[0]); a = -theta + np.pi / 2
rot = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
VA_r, VB_r = VA_r @ rot.T, VB_r @ rot.T
def norm(V):
    return (V - V.mean(0)) / (V.max(0) - V.min(0)).max()
A_n, B_n = norm(VA_r), norm(VB_r)

def draw(ax, V, F, title, heat=None):
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    light = np.array([0.3, 0.45, 0.84]); light /= np.linalg.norm(light)
    lam = np.clip(n @ light, 0, 1) * 0.6 + 0.35
    if heat is None:
        col = np.stack([lam * 0.86, lam * 0.78, lam * 0.70, np.ones_like(lam)], 1)
    else:
        hf = heat[F].mean(axis=1)
        hm = plt.cm.turbo(np.clip(hf / max(hf.max(), 1e-9), 0, 1))
        col = hm * (lam[:, None] * 0.55 + 0.45)
        col[:, 3] = 1.0
    ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolors='none'))
    ax.set_xlim(-0.42, 0.42); ax.set_ylim(-0.42, 0.42); ax.set_zlim(-0.45, 0.39)
    ax.view_init(elev=5, azim=90); ax.set_axis_off(); ax.set_title(title)

tr = trimesh.Trimesh(vertices=B_n, faces=FB, process=False)
cp, dvec, _ = trimesh.proximity.closest_point(tr, A_n)
heat_v = np.linalg.norm(A_n - cp, axis=1)
fig = plt.figure(figsize=(18, 7))
ax = fig.add_subplot(1, 3, 1, projection='3d'); draw(ax, A_n, FA, 'set2 photo (1.jpg actor) MICA')
ax = fig.add_subplot(1, 3, 2, projection='3d'); draw(ax, B_n, FB, 'set4 photo (ID photo) MICA')
ax = fig.add_subplot(1, 3, 3, projection='3d'); draw(ax, B_n, FB, 'shape diff heatmap', heat=heat_v)
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'mica_AB_diff.png'), dpi=120)
print('saved mica_AB_diff.png | disp mean %.2f mm max %.2f mm' % (heat_v.mean() * 322, heat_v.max() * 322))
