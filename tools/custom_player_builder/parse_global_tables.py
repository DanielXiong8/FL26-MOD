# -*- coding: utf-8 -*-
"""
Parse GlobalTables TextAsset to find the exact FaceTextureID -> name mapping.
Format: [int32 count] [bytes: string entries...] [int32 next_count] ...
Each string: [byte length] [utf8 chars]
"""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'

env = UnityPy.load(GAMEDATA)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read(check_read=False).m_Name == 'GlobalTables':
        raw = obj.read(check_read=False).m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)
        break

off = 0
tables = {}
while off < len(raw):
    count = struct.unpack_from("<I", raw, off)[0]
    off += 4
    entries = []
    for i in range(count):
        ln = raw[off]
        off += 1
        ent = raw[off:off+ln].decode('utf-8', errors='replace')
        off += ln
        entries.append(ent)
    # derive table name from first entry
    name = entries[0] if entries else f"table_{len(tables)}"
    tables[name] = entries
    print(f"Table {len(tables)}: {entries[0]} ({len(entries)} entries)")

print(f"\nTotal tables: {len(tables)}")

# --- Find the face table (it starts with "None" followed by "face_african") ---
face_table = None
face_idx = -1
for name, entries in tables.items():
    if entries[0] == 'None' and len(entries) > 5 and any('face_' in e for e in entries):
        face_table = entries
        print(f"\n=== FACE TABLE ({len(entries)} entries) ===")
        for i, e in enumerate(entries):
            print(f"  idx {i:3d}: {e}")
        break

# --- Find Ralla's texture: face_southeuropean_new3 ---
if face_table:
    for i, e in enumerate(face_table):
        if 'southeuropean_new3' in e:
            print(f"\n>>> Ralla's texture: {e} at INDEX {i} (byte1 = {i})")
        
        # Also find the table's ID range
        # Check: are there face textures NOT in the table? If yes, some are loaded at runtime
        # specifically by name pattern
    
    # Count how many "new" variants per family
    families = {}
    for e in face_table:
        if e.startswith('face_'):
            # extract base family name
            base = e.replace('_new1', '').replace('_new2', '').replace('_new3', '').replace('_new4', '').replace('_new5', '').replace('_new6', '')
            if base not in families:
                families[base] = []
            families[base].append(e)
    print(f"\n=== Face texture families in GlobalTables ===")
    for base, members in sorted(families.items()):
        indices = [face_table.index(e) for e in members]
        print(f"  {base}: {members} -> indices {indices}")

# Also check if all 87 avatar textures are in the table
print(f"\n=== Checking avatar textures vs GlobalTables ===")
env2 = UnityPy.load(r'C:\FL26_Mod\build\avatar.unity3d')
avatar_tex = set()
for obj in env2.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        n = getattr(d, 'm_Name', '') or ''
        if 'face' in n.lower():
            avatar_tex.add(n)
# generic families (av has "face_african", "face_african_new1" etc.; table has "face_african", "face_african_new1" etc.)
# Check which avatar textures are NOT in the table
if face_table:
    table_set = set(face_table)
    missing = [t for t in sorted(avatar_tex) if t not in table_set]
    print(f"Textures in avatar but NOT in GlobalTables ({len(missing)}):")
    for t in missing:
        print(f"  {t}")

# --- Dump ALL tables ---
print(f"\n=== ALL TABLES ===")
for name, entries in tables.items():
    print(f"\nTable: {name} ({len(entries)} entries)")
    for i, e in enumerate(entries):
        print(f"  {i:3d}: {e}")