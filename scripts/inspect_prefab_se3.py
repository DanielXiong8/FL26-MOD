# -*- coding: utf-8 -*-
# inspect_prefab_se3.py - enumerate all objects in avatar bundle: meshes, materials, texture refs
import UnityPy, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
env = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
meshes, mats = [], []
for files in env.file.files.values():
    try: objs = list(files.objects.values())
    except AttributeError:
        try: objs = list(files.objects)
        except AttributeError: continue
    for o in objs:
        try: tn = o.type.name
        except AttributeError: continue
        if tn == 'Mesh':
            try:
                m = o.read()
                meshes.append((getattr(m,'m_Name',''), len(getattr(m,'m_Vertices',b''))//3 if hasattr(m,'m_Vertices') else '?'))
            except Exception as e: meshes.append(('ERR',str(e)[:40]))
        elif tn == 'Material':
            try:
                mm = o.read()
                st = getattr(mm,'m_SavedProperties',None)
                texs = []
                if st:
                    for t in st.m_TexEnvs:
                        try:
                            td = t[1].m_Texture.read()
                            texs.append('%s=%s(%sx%s)' % (t[0], td.m_Name, td.m_Width, td.m_Height))
                        except Exception:
                            texs.append(t[0]+'=?')
                mats.append((mm.m_Name, '; '.join(texs)))
            except Exception as e: mats.append(('ERR',str(e)[:40]))
print('=== MESHES ===')
for n,c in meshes: print(n, c)
print('=== MATERIALS ===')
for n,t in mats: print(n, '|', t)
