# -*- coding: utf-8 -*-
"""extract_avatar_deps.py
Extract all face-related assets from avatar.unity3d for Unity Viewer use.
Output: C:\FL26_Mod\tools\FL26_AvatarPreviewer\extracted\
"""
import sys, os, json, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from PIL import Image
import UnityPy

SRC = r'C:\FL26_Mod\build\avatar.unity3d'
OUT = r'C:\FL26_Mod\tools\FL26_AvatarPreviewer\extracted'
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, 'meshes'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'textures'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'materials'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'shaders'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'gameobjects'), exist_ok=True)

env = UnityPy.load(SRC)
dep = {}  # dependency map

# --- Extract face_eastAsia_new1-6 meshes ---
face_names = ['face_EastAsia_new%d' % i for i in range(1, 7)]
for o in env.objects:
    if o.type.name == 'Mesh':
        m = o.read()
        if m.m_Name in face_names:
            tree = o.read_typetree()
            vd = tree['m_VertexData']
            data = bytes(vd['m_DataSize'])
            stride = 0
            for ch in vd['m_Channels']:
                if ch['stream'] == 0: stride = max(stride, ch['offset'] + ch['dimension'] * 4)
            n = vd['m_VertexCount']
            fl = np.frombuffer(data, np.float32)
            pos = fl[:n*stride//4].reshape(n, stride//4)[:, :3].tolist()
            uv0 = np.frombuffer(data[n*stride:], np.float32).reshape(-1, 2)[:n].tolist()
            idx = np.frombuffer(bytes(tree['m_IndexBuffer']), np.uint16).astype(int).tolist()
            subs = [{'firstByte': s['firstByte'], 'indexCount': s['indexCount']} for s in tree['m_SubMeshes']]
            # normals
            if 'm_Normals' in tree:
                normals = tree['m_Normals']
            else:
                # compute from positions
                normals = None
            bind_pose = tree.get('m_BindPose', [])
            out = {
                'name': m.m_Name,
                'vertexCount': n,
                'stride': stride,
                'positions': pos,
                'uv0': uv0,
                'indices': idx,
                'subMeshes': subs,
                'bindPose': bind_pose
            }
            path = os.path.join(OUT, 'meshes', m.m_Name + '.json')
            json.dump(out, open(path, 'w'), ensure_ascii=False, indent=1)
            dep[m.m_Name] = {'type': 'Mesh', 'path': 'meshes/' + m.m_Name + '.json'}
            print('Mesh:', m.m_Name, 'vc=%d' % n)

# --- Extract face textures ---
tex_names = ['face_eastasia_new%d' % i for i in range(1, 7)]
for o in env.objects:
    if o.type.name == 'Texture2D':
        t = o.read()
        if t.m_Name.lower() in tex_names:
            tree = o.read_typetree()
            img = t.image.convert('RGB')
            path = os.path.join(OUT, 'textures', t.m_Name + '.png')
            img.save(path)
            ts = tree.get('m_TextureSettings', {})
            tex_info = {
                'name': t.m_Name,
                'width': t.m_Width, 'height': t.m_Height,
                'format': tree.get('m_TextureFormat', ''),
                'wrapModeU': ts.get('m_WrapU', 0),
                'wrapModeV': ts.get('m_WrapV', 0),
                'filterMode': ts.get('m_FilterMode', 0),
                'aniso': ts.get('m_Aniso', 0),
            }
            json.dump(tex_info, open(os.path.join(OUT, 'textures', t.m_Name + '.meta.json'), 'w'), indent=1)
            dep[t.m_Name] = {'type': 'Texture2D', 'path': 'textures/' + t.m_Name + '.png'}
            print('Texture:', t.m_Name, img.size)

# --- Extract skin_eastAsia_new1 ---
for o in env.objects:
    if o.type.name == 'Texture2D':
        t = o.read()
        if t.m_Name == 'skin_eastAsia_new1':
            img = t.image.convert('RGB')
            img.save(os.path.join(OUT, 'textures', 'skin_eastAsia_new1.png'))
            dep['skin_eastAsia_new1'] = {'type': 'Texture2D', 'path': 'textures/skin_eastAsia_new1.png'}
            print('Texture: skin_eastAsia_new1')
            break

# --- Extract Materials ---
for o in env.objects:
    if o.type.name == 'Material':
        m = o.read()
        if 'eastasia' in m.m_Name.lower() or 'face' in m.m_Name.lower():
            tree = o.read_typetree()
            mat = {
                'name': m.m_Name,
                'shader': tree.get('m_Shader', {}),
                'savedProperties': tree.get('m_SavedProperties', {}),
                'floatProperties': tree.get('m_Floats', {}),
                'colorProperties': tree.get('m_Colors', {}),
                'texEnv': tree.get('m_TexEnvs', {}),
            }
            path = os.path.join(OUT, 'materials', m.m_Name + '.json')
            json.dump(mat, open(path, 'w'), ensure_ascii=False, indent=1)
            dep[m.m_Name] = {'type': 'Material', 'path': 'materials/' + m.m_Name + '.json'}
            print('Material:', m.m_Name)

# --- Extract Shaders ---
for o in env.objects:
    if o.type.name == 'Shader':
        sh = o.read()
        tree = o.read_typetree()
        sname = tree.get('m_ParsedForm', {}).get('m_Name', 'unnamed')
        path = os.path.join(OUT, 'shaders', sname.replace('/', '_') + '.json')
        json.dump(tree, open(path, 'w'), ensure_ascii=False, indent=1)
        dep[sname] = {'type': 'Shader', 'path': 'shaders/' + sname.replace('/', '_') + '.json'}
        print('Shader:', sname)

# --- Extract GameObjects (face-related) ---
face_go_names = ['face_EastAsia_new%d' % i for i in range(1, 7)]
for o in env.objects:
    if o.type.name == 'GameObject':
        go = o.read()
        if go.m_Name in face_go_names:
            tree = o.read_typetree()
            path = os.path.join(OUT, 'gameobjects', go.m_Name + '.json')
            json.dump(tree, open(path, 'w'), ensure_ascii=False, indent=1)
            dep[go.m_Name] = {'type': 'GameObject', 'path': 'gameobjects/' + go.m_Name + '.json'}
            print('GameObject:', go.m_Name)

# --- Extract SkinnedMeshRenderer for face objects ---
for o in env.objects:
    if o.type.name == 'SkinnedMeshRenderer':
        smr = o.read()
        tree = o.read_typetree()
        if 'face' in tree.get('m_GameObject', {}).get('m_Name', '').lower():
            path = os.path.join(OUT, 'gameobjects', 'SkinnedMeshRenderer_face.json')
            with open(path, 'w') as f:
                json.dump(tree, f, ensure_ascii=False, indent=1)
            dep['SkinnedMeshRenderer_face'] = {'type': 'SkinnedMeshRenderer', 'path': 'gameobjects/SkinnedMeshRenderer_face.json'}
            print('SMR (face) extracted')

# --- Write dependency map ---
dep_path = os.path.join(OUT, 'dependency_map.json')
json.dump(dep, open(dep_path, 'w'), ensure_ascii=False, indent=1)
print('\nDependency map ->', dep_path)
print('Done. Extract path:', OUT)