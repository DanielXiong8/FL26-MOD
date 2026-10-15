# -*- coding: utf-8 -*-
"""
Generate mesh_uv.json, mesh_topology.json, and overlay UV on face texture.
"""
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy
from PIL import Image

AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
OUT = r'C:\FL26_Mod\work\face_pipeline\uv'
os.makedirs(OUT, exist_ok=True)

env = UnityPy.load(AVATAR)

# 1. extract face_african_new1 texture
tex_img = None
for obj in env.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_african_new1':
            tex_img = d.image
            tex_img.save(os.path.join(OUT, 'face_african_new1_extracted.png'))
            print("Saved face_african_new1_extracted.png")
            break

# 2. extract mesh_uv.json and mesh_topology.json with REAL UV (ch4)
for obj in env.objects:
    if obj.type.name == 'Mesh':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_African_new1':
            mesh = d
            break

vd = mesh.m_VertexData
data = bytes(vd.m_DataSize)
VCOUNT = 700
s0_base = 0
s1_base = 40 * VCOUNT

verts, uvs, normals = [], [], []
for i in range(VCOUNT):
    # pos
    p_off = s0_base + i * 40 + 0
    x, y, z = struct.unpack_from('<fff', data, p_off)
    verts.append((x, y, z))
    # normal
    n_off = s0_base + i * 40 + 12
    nx, ny, nz = struct.unpack_from('<fff', data, n_off)
    normals.append((nx, ny, nz))
    # uv0 (ch4)
    u_off = s1_base + i * 16 + 0
    u, v = struct.unpack_from('<ff', data, u_off)
    uvs.append((u, v))

# indices
ib = bytes(mesh.m_IndexBuffer)
tris = list(struct.unpack(f'<{len(ib)//2}H', ib))

print(f"Extracted {len(verts)} verts, {len(uvs)} uvs, {len(tris)//3} triangles")

# save mesh_uv.json
uv_records = [{'vertex_index': i, 'u': round(u, 6), 'v': round(v, 6)} for i, (u, v) in enumerate(uvs)]
with open(os.path.join(OUT, 'mesh_uv.json'), 'w') as f:
    json.dump({'mesh': 'face_African_new1', 'uv_count': len(uv_records), 'uv': uv_records}, f, indent=2)

# save mesh_topology.json
tri_records = [{'triangle_index': i//3, 'v0': tris[i], 'v1': tris[i+1], 'v2': tris[i+2]} for i in range(0, len(tris)-2, 3)]
with open(os.path.join(OUT, 'mesh_topology.json'), 'w') as f:
    json.dump({
        'mesh': 'face_African_new1',
        'vertex_count': len(verts),
        'vertices': [{'index': i, 'x': round(x,5), 'y': round(y,5), 'z': round(z,5), 'nx': round(nx,5), 'ny': round(ny,5), 'nz': round(nz,5)} for i, ((x,y,z),(nx,ny,nz)) in enumerate(zip(verts, normals))],
        'triangles': tri_records,
        'submesh_count': len(getattr(mesh, 'm_SubMeshes', []))
    }, f, indent=2)

# 3. plot UV wireframe over texture
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 8))
if tex_img:
    ax.imshow(tex_img, extent=[0, 1, 0, 1], origin='lower')

# plot triangles
for t in tri_records:
    u0, v0 = uvs[t['v0']]
    u1, v1 = uvs[t['v1']]
    u2, v2 = uvs[t['v2']]
    ax.plot([u0, u1, u2, u0], [v0, v1, v2, v0], 'r-', linewidth=0.3, alpha=0.7)

ax.scatter([u for u, v in uvs], [v for u, v in uvs], s=1.5, c='yellow', alpha=0.9)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_title("FL26 Mesh UV Wireframe overlaid on face_african_new1.png")
plt.savefig(os.path.join(OUT, 'uv_preview.png'), dpi=200, bbox_inches='tight')
print("Saved uv_preview.png with texture overlay!")
