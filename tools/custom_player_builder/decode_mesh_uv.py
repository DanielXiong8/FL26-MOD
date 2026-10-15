# -*- coding: utf-8 -*-
"""
Decode Unity VertexData for face meshes (e.g. face_African_new1 / Head_Haaland_lod1).
Unity Mesh VertexData binary layout:
  m_Channels: array of ChannelInfo (stream, offset, format, dimension)
  m_Streams: array of StreamInfo (channelMask, offset, stride, dividerOp, frequency)
  m_DataSize: raw bytes
Format 0 = kVertexFormatFloat (4 bytes per component)
"""
import sys, io, os, json, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
OUT = r'C:\FL26_Mod\work\face_pipeline\uv'
os.makedirs(OUT, exist_ok=True)

env = UnityPy.load(AVATAR)

def decode_mesh(mesh_name):
    target = None
    for obj in env.objects:
        if obj.type.name == 'Mesh':
            try:
                d = obj.read(check_read=False)
                if d.m_Name == mesh_name:
                    target = d
                    break
            except Exception:
                pass
    if not target:
        print(f"Mesh {mesh_name} not found")
        return

    vd = target.m_VertexData
    vcount = getattr(target, 'm_VertexCount', 0)
    data = bytes(vd.m_DataSize if isinstance(vd.m_DataSize, (bytes, bytearray)) else vd.m_DataSize)
    channels = list(vd.m_Channels)
    
    # UnityPy 2.x sometimes doesn't expose m_Streams directly
    try:
        streams = list(vd.m_Streams)
    except (TypeError, AttributeError):
        # derive stream info manually
        class FakeStream: pass
        streams = []
        current_stream_idx = -1
        current_offset = 0
        for ch in channels:
            if ch.dimension == 0: continue
            if ch.stream != current_stream_idx:
                current_stream_idx = ch.stream
                s = FakeStream()
                s.offset = current_offset
                s.stride = 0
                streams.append(s)
            ch.offset = streams[-1].stride
            streams[-1].stride += ch.dimension * 4  # assuming 4 bytes per component (float32)
        
        # fix offsets based on stream
        for i, s in enumerate(streams):
            if i > 0:
                s.offset = streams[i-1].offset + streams[i-1].stride * vcount
    
    print(f"Mesh: {mesh_name} | vcount={vcount} | streams={len(streams)} | raw data bytes={len(data)}")

    # inspect streams
    if not streams:
        print("Failed to derive streams")
        return

    s0 = streams[0]
    s1 = streams[1] if len(streams) > 1 else None

    # calculate vertex count if vcount is 0
    if vcount == 0 and streams:
        total_stride = sum(s.stride for s in streams)
        if total_stride > 0:
            vcount = len(data) // total_stride
        print(f"Inferred vcount = {vcount} (total_stride={total_stride})")

    verts = []
    for i in range(vcount):
        off = s0.offset + i * s0.stride + channels[0].offset
        if off + 12 <= len(data):
            x, y, z = struct.unpack_from('<fff', data, off)
            verts.append((x, y, z))

    uv0 = []
    if s1 and channels[4].dimension == 2:
        for i in range(vcount):
            off = s1.offset + i * s1.stride + channels[4].offset
            if off + 8 <= len(data):
                u, v = struct.unpack_from('<ff', data, off)
                uv0.append((u, v))

    # index buffer
    ib = bytes(target.m_IndexBuffer)
    fmt = getattr(target, 'm_IndexFormat', 0)
    if fmt == 0:
        tris = list(struct.unpack(f'<{len(ib)//2}H', ib))
    else:
        tris = list(struct.unpack(f'<{len(ib)//4}I', ib))

    print(f"Decoded: verts={len(verts)}, uv0={len(uv0)}, tris={len(tris)//3}")
    if uv0:
        print(f"UV0 sample: {uv0[:5]}")
        print(f"UV0 min/max: u=[{min(u for u,v in uv0):.3f}, {max(u for u,v in uv0):.3f}], v=[{min(v for u,v in uv0):.3f}, {max(v for u,v in uv0):.3f}]")

    # save JSON
    uv_records = [{'vertex_index': i, 'u': round(u, 6), 'v': round(v, 6)} for i, (u, v) in enumerate(uv0)]
    tri_records = [{'triangle_index': i//3, 'v0': tris[i], 'v1': tris[i+1], 'v2': tris[i+2]} for i in range(0, len(tris)-2, 3)]

    with open(os.path.join(OUT, 'mesh_uv.json'), 'w') as f:
        json.dump({'mesh': mesh_name, 'uv_count': len(uv_records), 'uv': uv_records}, f, indent=2)

    with open(os.path.join(OUT, 'mesh_topology.json'), 'w') as f:
        json.dump({
            'mesh': mesh_name,
            'vertex_count': len(verts),
            'vertices': [{'index': i, 'x': round(x,5), 'y': round(y,5), 'z': round(z,5)} for i, (x,y,z) in enumerate(verts)],
            'triangles': tri_records,
            'submesh_count': len(getattr(target, 'm_SubMeshes', []))
        }, f, indent=2)

    # render preview scatter
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.figure(figsize=(7, 7))
    plt.scatter([u for u, v in uv0], [v for u, v in uv0], s=2, c='blue', alpha=0.6)
    plt.title(f'UV Map: {mesh_name} ({len(uv0)} vertices)')
    plt.xlabel('U')
    plt.ylabel('V')
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.savefig(os.path.join(OUT, 'uv_preview.png'), dpi=150)
    print(f"Saved uv_preview.png, mesh_uv.json, mesh_topology.json")

print("--- Testing face_African_new1 ---")
decode_mesh('face_African_new1')
