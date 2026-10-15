# -*- coding: utf-8 -*-
"""
Track D §2/§5: Investigate FaceTextureID → Texture mapping.
Key questions:
1. What does material 'face' _MainTex path ID 2823274851336602280 resolve to?
2. Is there a TextAsset mapping table for FaceTextureID → texture name?
3. How does the game dynamically swap textures at runtime?
4. Check if there's a name-based convention (face_southeuropean_new3 → face texture ID 30)
"""
import sys, io, os, struct, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'

# --- 1. avatar bundle: material 'face' _MainTex path ID resolution ---
env = UnityPy.load(AVATAR)

# dump all objects with their path IDs
print("=== avatar.unity3d ALL objects with path IDs ===")
path_ids = {}
for obj in env.objects:
    pid = obj.path_id
    t = obj.type.name
    try:
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '') or ''
    except:
        name = ''
    path_ids[pid] = (t, name)

# specific path ID search
TARGET_PID = 2823274851336602280
print(f"Path ID {TARGET_PID} resolves to: {path_ids.get(TARGET_PID)}")

# also search for negative path IDs (common in Unity)
print(f"\nPath ID {TARGET_PID} by negative: {path_ids.get(TARGET_PID, 'NOT FOUND')}")

# search for face-related textures
face_textures = [(pid, name) for pid, (t, name) in path_ids.items() if t == 'Texture2D' and 'face' in name.lower()]
print(f"\n=== Face textures in avatar ({len(face_textures)}) ===")
for pid, name in sorted(face_textures, key=lambda x: x[1]):
    print(f"  PID {pid:20d}: {name}")

# --- 2. Check if there's a mapping asset in gamedata ---
env2 = UnityPy.load(GAMEDATA)
print("\n=== gamedata.unity3d: TextAssets with 'face'/'texture'/'appearance' names ===")
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '') or ''
        if any(k in name.lower() for k in ['face', 'texture', 'appear', 'head', 'skin', 'look']):
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', errors='surrogateescape')
            raw_bytes = bytes(raw)
            # show first 200 chars or hex
            text = raw_bytes.decode('utf-8', errors='replace')
            print(f"\n  === {name} ({len(raw_bytes)} bytes) ===")
            print(text[:500])
            print("...")

# --- 3. Check if there's a Texture2D in gamedata as well (maybe the mapping is in Here) ---
print("\n=== gamedata.unity3d: Texture2D count ===")
tex_count = sum(1 for obj in env2.objects if obj.type.name == 'Texture2D')
print(f"  Texture2Ds in gamedata: {tex_count}")

# --- 4. Check 'face' material more carefully ---
print("\n=== Material 'face' full dependency chain ===")
for obj in env.objects:
    if obj.type.name == 'Material':
        d = obj.read(check_read=False)
        if d.m_Name == 'face':
            # dump all properties
            sp = d.m_SavedProperties
            print(f"  Material: {d.m_Name}")
            print(f"  Shader: {getattr(d.m_Shader, 'm_PathID', 'N/A')}")
            # Check both TexEnvs and Floats/Colors
            print(f"  TexEnvs count: {len(sp.m_TexEnvs)}")
            for pair in sp.m_TexEnvs:
                k = pair[0] if isinstance(pair, tuple) else pair.first
                v = pair[1] if isinstance(pair, tuple) else pair.second
                tex = v.m_Texture
                print(f"  TexEnv: {k} -> pathID={getattr(tex, 'm_PathID', None)}, fileID={getattr(tex, 'm_FileID', None)}")
            # Check if there's a way to find the exact texture name referenced
            # Unity's serialized reference: pathID + fileID + name
            # fileID 0 = same bundle
            for pair in sp.m_TexEnvs:
                k = pair[0] if isinstance(pair, tuple) else pair.first
                v = pair[1] if isinstance(pair, tuple) else pair.second
                tex = v.m_Texture
                pid = getattr(tex, 'm_PathID', None)
                if pid and pid in path_ids:
                    print(f"  -> {k} resolves to: {path_ids[pid]}")
                else:
                    print(f"  -> {k}: pathID={pid} NOT IN BUNDLE (likely modified at runtime)")
            break

# --- 5. Check if FaceTextureID mapping is in a global table ---
print("\n=== gamedata.unity3d: looking for structured data files ===")
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '') or ''
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        raw_bytes = bytes(raw)
        # Check for CSV with 'face' or 'head' or 'id' in first 100 chars
        text = raw_bytes.decode('utf-8', errors='replace')[:500]
        if 'face' in text.lower() or 'head' in text.lower() or 'texture' in text.lower():
            print(f"  {name}: {text[:200]}")
        # Check for cleaner tables
        if 'hair' in text.lower() or 'skin' in text.lower():
            print(f"  {name}: {text[:200]}")