# -*- coding: utf-8 -*-
"""
Definitive test: is byte1 a direct index into GlobalTables face table?
Compare known star players' byte1 with their unique texture name's index.
"""
import sys, io, struct, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'

# ---- 1. Parse GlobalTables robustly: parse the 81-entry face table ----
env = UnityPy.load(GAMEDATA)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read(check_read=False).m_Name == 'GlobalTables':
        raw = obj.read(check_read=False).m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        raw = bytes(raw)
        break

# We know the face table starts at offset 0x184 with count 0x51 (81)
# But let's parse sequentially with bounds; find the face table by scanning
def parse_tables(raw):
    off = 0
    all_tables = []
    while off < len(raw):
        if off + 4 > len(raw): break
        count = struct.unpack_from("<I", raw, off)[0]
        if count > 5000 or count == 0: 
            break  # safety
        off += 4
        entries = []
        ok = True
        for i in range(count):
            if off >= len(raw):
                ok = False; break
            ln = raw[off]; off += 1
            if off + ln > len(raw):
                ok = False; break
            entries.append(raw[off:off+ln].decode('utf-8', errors='replace'))
            off += ln
        if not ok:
            break
        all_tables.append(entries)
    return all_tables

tables = parse_tables(raw)
print(f"parsed {len(tables)} tables")
for ti, t in enumerate(tables):
    print(f"  Table {ti}: {len(t)} entries, first={t[0] if t else '?'}")

# find face table: contains face_african and face_Haaland
face_table = None
for t in tables:
    if any('face_Haaland' in e for e in t) or any('face_african' in e for e in t):
        if any('face_' in e for e in t) and len(t) > 10:
            face_table = t
            break

if face_table is None:
    # fallback: the table right after None(24) None(12) None(8) None(81)
    print("face_table not found by name search")
    face_table = tables[3] if len(tables) > 3 else None

if face_table:
    print(f"\n=== FACE TABLE ({len(face_table)} entries) ===")
    tex_index = {}
    for i, e in enumerate(face_table):
        print(f"  idx {i:3d}: {e}")
        tex_index[e] = i

# ---- 2. Get appearance byte1 for known star players ----
# find pids by name (Haaland, Mbappe, Foden, Messi, Ronaldo)
env2 = UnityPy.load(GAMEDATA)
assets = {}
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'PlayerAppearanceTable'):
            rr = d.m_Script
            assets[d.m_Name] = rr.encode('utf-8', errors='surrogateescape') if isinstance(rr, str) else bytes(rr)

# parse players: pid, name
raw = assets['Players']
off = 8
ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
players = {}
for _ in range(pcnt):
    pid = struct.unpack_from("<I", raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2
    name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    off += 8 + 3 + 17 + 2 + 1 + 4
    players[pid] = name

# appearance
pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
app = {}
for i in range(n):
    k, o = struct.unpack_from("<II", pa, 4 + i*8)
    app[k] = pa[o+4:o+21]

def find_player_pid(surname_substr):
    for pid, name in players.items():
        if surname_substr.lower() in name.lower():
            return pid, name
    return None, None

print("\n=== Star player byte1 vs GlobalTables index ===")
targets = ['Haaland', 'Mbappe', 'Foden', 'Messi', 'Ronaldo', 'Rodri', 'Bellingham', 'salah']
for name_sub in targets:
    pid, pname = find_player_pid(name_sub)
    if pid and pid in app:
        b1 = app[pid][1]
        # guess texture name
        guess = None
        for ename in ['face_' + name_sub, 'face_' + name_sub.lower(), 'face_c_Ronaldo', 'face_messi']:
            if ename in tex_index:
                guess = (ename, tex_index[ename])
        print(f"  {pname} (pid {pid}): byte1={b1} | GlobalTables: {guess}")
    else:
        print(f"  {name_sub}: player/appearance not found")
