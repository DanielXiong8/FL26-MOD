# -*- coding: utf-8 -*-
"""Diagnose VertexData channels: sample values per channel to locate real UV channel."""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')

for obj in env.objects:
    if obj.type.name == 'Mesh':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_African_new1':
            mesh = d
            break

vd = mesh.m_VertexData
data = bytes(vd.m_DataSize)
channels = list(vd.m_Channels)

# stream layout (from previous analysis): strides 40/16/16, vcount=700
VCOUNT = 700
stream_base = {0: 0, 1: 40 * VCOUNT, 2: (40 + 16) * VCOUNT}
stream_stride = {0: 40, 1: 16, 2: 16}

FMT_SIZE = {0: 4, 10: 4, 1: 2}

print("Channels with dim>0, first 3 vertices each:")
for ci, ch in enumerate(channels):
    if ch.dimension == 0:
        continue
    sz = FMT_SIZE.get(ch.format, 4)
    base = stream_base[ch.stream]
    stride = stream_stride[ch.stream]
    print(f"\nch{ci}: stream={ch.stream} offset={ch.offset} fmt={ch.format} dim={ch.dimension}")
    samples = []
    allmin, allmax = 1e9, -1e9
    for vi in range(VCOUNT):
        off = base + vi * stride + ch.offset
        vals = []
        for c in range(ch.dimension):
            if ch.format == 0:
                v = struct.unpack_from('<f', data, off + c * 4)[0]
            elif ch.format == 10:
                v = struct.unpack_from('<I', data, off + c * 4)[0]
            else:
                v = struct.unpack_from('<e', data, off + c * 2)[0]
            vals.append(round(v, 4))
            if isinstance(v, float):
                allmin = min(allmin, v); allmax = max(allmax, v)
        if vi < 3:
            samples.append(vals)
    for s in samples:
        print("   ", s)
    print(f"    range over {VCOUNT} verts: [{allmin:.4f}, {allmax:.4f}]")
