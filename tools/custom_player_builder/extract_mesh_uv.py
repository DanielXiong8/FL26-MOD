# -*- coding: utf-8 -*-
"""
Track B1/B2: avatar.unity3d inventory + face mesh UV extraction.
Outputs to C:\\FL26_Mod\\work\\face_pipeline\\uv\\
"""
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
OUT = r'C:\FL26_Mod\work\face_pipeline\uv'
os.makedirs(OUT, exist_ok=True)

env = UnityPy.load(AVATAR)

# ---------- inventory ----------
by_type = {}
for obj in env.objects:
    by_type.setdefault(obj.type.name, []).append(obj)

print("=== avatar.unity3d inventory ===")
for t in sorted(by_type):
    print(f"  {t}: {len(by_type[t])}")

meshes = {}
materials = {}
textures = {}
renderers = []
for t, objs in by_type.items():
    for obj in objs:
        try:
            d = obj.read(check_read=False)
        except Exception:
            continue
        name = getattr(d, 'm_Name', '') or ''
        if t == 'Mesh':
            meshes[name] = obj
        elif t == 'Material':
            materials[name] = obj
        elif t == 'Texture2D':
            textures[name] = obj
        elif t in ('SkinnedMeshRenderer', 'MeshRenderer'):
            renderers.append((name, obj))

face_tex = sorted([n for n in textures if 'face' in n.lower()])
face_mesh = sorted([n for n in meshes if 'face' in n.lower() or 'head' in n.lower()])
face_mat = sorted([n for n in materials if 'face' in n.lower() or 'head' in n.lower()])
print(f"\nFace textures ({len(face_tex)}): {face_tex[:15]}")
print(f"Face/head meshes ({len(face_mesh)}): {face_mesh[:15]}")
print(f"Face/head materials ({len(face_mat)}): {face_mat[:15]}")

# ---------- material -> texture dependency ----------
print("\n=== Material m_TexEnvs (face-related materials) ===")
target_tex_names = [n for n in textures if 'african' in n.lower()]
print(f"african textures: {target_tex_names}")

def mat_links(mname):
    try:
        d = materials[mname].read(check_read=False)
        envs = d.m_SavedProperties.m_TexEnvs
        out = []
        for pair in envs:
            k = pair[0] if isinstance(pair, tuple) else pair.first
            v = pair[1] if isinstance(pair, tuple) else pair.second
            tex = getattr(v, 'm_Texture', None)
            out.append((str(k), getattr(tex, 'm_PathID', None), getattr(tex, 'm_FileID', None)))
        return out
    except Exception as e:
        return [('ERR', str(e), None)]

for mn in face_mat[:10]:
    print(f"  {mn}: {mat_links(mn)}")

# ---------- pick face mesh, dump basic stats ----------
print("\n=== Face mesh candidates detail ===")
for mn in face_mesh[:10]:
    try:
        m = meshes[mn].read()
        vc = getattr(m, 'm_VertexCount', '?')
        sm = len(getattr(m, 'm_SubMeshes', []))
        print(f"  {mn}: verts={vc} submeshes={sm}")
    except Exception as e:
        print(f"  {mn}: error {e}")

picked = face_mesh[0] if face_mesh else sorted(meshes)[0]
print(f"\nPicked mesh for UV extraction: {picked}")
mesh = meshes[picked].read()

# ---------- extract verts / uv / tris ----------
verts, uv0, uv1, tris = [], [], [], []
vcount = int(getattr(mesh, 'm_VertexCount', 0) or 0)

def flat_floats(attr, per):
    arr = getattr(mesh, attr, None)
    if arr is None:
        return []
    try:
        vals = list(arr)
    except Exception:
        return []
    if per == 3:
        return [(vals[i*3], vals[i*3+1], vals[i*3+2]) for i in range(min(vcount, len(vals)//3))]
    return [(vals[i*2], vals[i*2+1]) for i in range(min(vcount, len(vals)//2))]

verts = flat_floats('m_Vertices', 3)
uv0 = flat_floats('m_UV0', 2)
uv1 = flat_floats('m_UV1', 2)

# index buffer
tris = []
try:
    ib = bytes(mesh.m_IndexBuffer)
    fmt = int(getattr(mesh, 'm_IndexFormat', 0) or 0)  # 0=UInt16, 1=UInt32
    if fmt == 0:
        tris = list(struct.unpack(f'<{len(ib)//2}H', ib))
    else:
        tris = list(struct.unpack(f'<{len(ib)//4}I', ib))
except Exception as e:
    print('index buffer error:', e)

print(f"extracted: verts={len(verts)} uv0={len(uv0)} uv1={len(uv1)} indices={len(tris)}")

# fallback: parse m_VertexData channels if direct arrays empty
if not uv0:
    print("direct UV arrays empty; trying m_VertexData channel parse...")
    try:
        vd = mesh.m_VertexData
        chans = list(vd.m_Channels)
        data = bytes(vd.m_DataSize if isinstance(vd.m_DataSize, (bytes, bytearray)) else vd.m_DataSize)
        print(f"  channels: {len(chans)}, data bytes: {len(data)}")
        # channel order in Unity: 0=pos,1=normal,2=tangent,3=color,4=uv0,...
        for ci, ch in enumerate(chans):
            print(f"  ch{ci}: dim={ch.dimension} fmt={ch.format} stream={ch.stream} offset={ch.offset}")
    except Exception as e:
        print("VertexData parse failed:", e)

# ---------- write outputs ----------
uv_records = [{'vertex_index': i, 'u': round(u, 6), 'v': round(v, 6)} for i, (u, v) in enumerate(uv0)]
tri_records = [{'triangle_index': i//3, 'v0': tris[i], 'v1': tris[i+1], 'v2': tris[i+2]} for i in range(0, len(tris)-2, 3)]

with open(os.path.join(OUT, 'mesh_uv.json'), 'w') as f:
    json.dump({'mesh': picked, 'uv_count': len(uv_records), 'uv': uv_records}, f)

with open(os.path.join(OUT, 'mesh_topology.json'), 'w') as f:
    json.dump({
        'mesh': picked,
        'vertex_count_total': len(verts),
        'triangles': tri_records,
        'submesh_count': len(getattr(mesh, 'm_SubMeshes', [])),
        'has_uv1': bool(uv1),
    }, f)
print(f"\nmesh_uv.json ({len(uv_records)} uv), mesh_topology.json ({len(tri_records)} tris) written")

# ---------- uv preview ----------
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6, 6))
    plt.scatter([u for u, v in uv0], [v for u, v in uv0], s=0.5)
    plt.gca().set_aspect('equal'); plt.xlim(0, 1); plt.ylim(0, 1)
    plt.title(f'UV0: {picked}')
    plt.savefig(os.path.join(OUT, 'uv_preview.png'), dpi=120)
    print("uv_preview.png saved")
except ImportError:
    W = H = 512
    img = bytearray([255] * (W * H * 3))
    for u, v in uv0:
        x = min(W-1, max(0, int(u * W))); y = min(H-1, max(0, int((1-v) * H)))
        i = (y * W + x) * 3
        img[i:i+3] = b'\x00\x00\x00'
    with open(os.path.join(OUT, 'uv_preview.ppm'), 'wb') as f:
        f.write(f'P6\n{W} {H}\n255\n'.encode() + bytes(img))
    print('uv_preview.ppm saved (no matplotlib)')

print('\nDONE')
