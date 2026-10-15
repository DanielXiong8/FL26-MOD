# -*- coding: utf-8 -*-
"""
Track D: Find FaceTextureID -> texture mapping mechanism.
Search ALL assets (TextAsset, MonoBehaviour, ScriptableObject) for the
texture family name strings, to locate the registry/table that maps
byte1 IDs to texture names. Also dump full face texture list with byte1.
"""
import sys, io, os, struct, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'
AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'

# ---- 1. full face texture name list from avatar ----
env = UnityPy.load(AVATAR)
tex_names = []
tex_by_pid = {}
for obj in env.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        n = getattr(d, 'm_Name', '') or ''
        if 'face' in n.lower():
            tex_names.append(n)
            tex_by_pid[obj.path_id] = n
print(f"=== face textures ({len(tex_names)}) ===")
for n in sorted(set(tex_names)):
    print("  ", n)

# ---- 2. search ALL objects in avatar for the family-name strings ----
print("\n=== avatar: searching all objects for 'southeuropean' / family names ===")
search_terms = ['southeuropean_new3', 'southeuropean', 'face_southeuropean', 'northeuropean', 'FaceTexture']
for obj in env.objects:
    t = obj.type.name
    if t in ('TextAsset', 'MonoBehaviour', 'ScriptableObject', 'Sprite', 'SpriteAtlas'):
        try:
            d = obj.read(check_read=False)
            # for TextAsset, read m_Script; for others try to stringify
            raw = None
            if t == 'TextAsset':
                raw = d.m_Script
                if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
                raw = bytes(raw)
            elif t == 'MonoBehaviour':
                raw = bytes(d.m_Script) if hasattr(d, 'm_Script') and isinstance(getattr(d,'m_Script',None), (bytes, bytearray)) else None
            if raw:
                text = raw.decode('utf-8', errors='replace')
                for term in ['southeuropean', 'northeuropean', 'face_']:
                    if term in text:
                        print(f"  [{t}] pid={obj.path_id} name={getattr(d,'m_Name','')!r} contains '{term}'")
                        break
        except Exception as e:
            pass

# ---- 3. search gamedata for mapping ----
print("\n=== gamedata: searching for 'southeuropean' / 'face_' in TextAssets ===")
env2 = UnityPy.load(GAMEDATA)
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)
        text = raw.decode('utf-8', errors='replace')
        if 'southeuropean' in text or 'northeuropean' in text or 'face_african' in text:
            print(f"  gamedata TextAsset '{getattr(d,'m_Name','')}' contains face-family names ({len(raw)} bytes)")
            # print context
            idx = text.find('southeuropean')
            print("   context:", text[max(0,idx-50):idx+80].replace('\n',' '))

# ---- 4. check MonoBehaviour with m_Script as string (serialized) ----
print("\n=== gamedata: MonoBehaviours containing face names (serialized) ===")
for obj in env2.objects:
    if obj.type.name == 'MonoBehaviour':
        try:
            d = obj.read(check_read=False)
            s = getattr(d, 'm_Script', None)
            if isinstance(s, str):
                if 'southeuropean' in s or 'face_african' in s:
                    print(f"  MonoBehaviour pid={obj.path_id} contains face-family strings")
            elif isinstance(s, bytes):
                if b'southeuropean' in s or b'face_african' in s:
                    print(f"  MonoBehaviour pid={obj.path_id} (bytes) contains face-family strings")
        except Exception:
            pass

print("\n=== done ===")
