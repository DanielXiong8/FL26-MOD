# -*- coding: utf-8 -*-
"""
face_texture_registry v2: token-level matching.
Also: dump all 83 face textures, and correlate GENERIC b1 IDs (29-33...)
with player nationality stats to identify generic texture families.
"""
import struct, sys, io, os, csv, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy
from collections import Counter, defaultdict

BUNDLE = r'C:\FL26_Mod\build\gamedata.unity3d'
AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'
OUT = r'C:\FL26_Mod\recon\03_player'

env2 = UnityPy.load(AVATAR)
tex_names = []
for obj in env2.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        if d.m_Name and 'face' in d.m_Name.lower():
            tex_names.append(d.m_Name)
print("=== ALL face textures ===")
for t in sorted(tex_names):
    print("  ", t)

env = UnityPy.load(BUNDLE)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'PlayerAppearanceTable'):
            raw = d.m_Script
            assets[d.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

raw = assets['Players']
off = 8
ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
players = []
for _ in range(pcnt):
    pid = struct.unpack_from("<I", raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2
    name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
    off += 3 + 17 + 2 + 1 + 4
    players.append((pid, name, nat))

pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
app = {}
for i in range(n):
    k, o = struct.unpack_from("<II", pa, 4 + i*8)
    app[k] = pa[o+4:o+21]

def tokens(s):
    return [t for t in re.split(r"[^a-zA-Z0-9]+", s) if t]

# texture candidate names: strip face_/Face_ prefix
tex_tokens = {}
for t in tex_names:
    part = re.sub(r'^face_', '', t, flags=re.IGNORECASE)
    toks = [x for x in tokens(part) if len(x) >= 4]
    if toks:
        tex_tokens[t] = toks

# token -> textures (unique-token index)
tok2tex = defaultdict(set)
for t, toks in tex_tokens.items():
    for x in toks:
        tok2tex[x].add(t)
uniq_tok = {x: next(iter(s)) for x, s in tok2tex.items() if len(s) == 1}

matches = []
for pid, name, nat in players:
    ptoks = [x for x in tokens(name) if len(x) >= 4]
    hits = set()
    for x in ptoks:
        if x in uniq_tok:
            hits.add(uniq_tok[x])
    if len(hits) == 1:
        a = app.get(pid)
        if a:
            matches.append((pid, name, nat, hits.pop(), a))

print(f"\ntoken-unique matches: {len(matches)}")
tex_count = Counter(m[3] for m in matches)
print(f"textures matched: {len(tex_count)} / {len(tex_names)}")
for t, c in tex_count.most_common():
    print(f"  {t}: {c} player(s)")

print("\n=== byte1 per matched texture (star textures) ===")
tex_b1 = defaultdict(Counter)
for pid, name, nat, tex, a in matches:
    tex_b1[tex][a[1]] += 1
for tex in sorted(tex_b1):
    print(f"  {tex}: b1={dict(tex_b1[tex])}")

# generic b1 (29-33 etc) nationality stats
print("\n=== generic b1 -> nationality (top5) ===")
b1_nat = defaultdict(Counter)
for pid, name, nat, tex, a in matches:
    b1_nat[a[1]][nat] += 1
# also across ALL players
b1_nat_all = defaultdict(Counter)
for pid, name, nat in players:
    a = app.get(pid)
    if a:
        b1_nat_all[a[1]][nat] += 1
for b1 in sorted(set(list(b1_nat.keys()) + [29,30,31,32,33])):
    allc = b1_nat_all.get(b1, Counter())
    tot = sum(allc.values())
    print(f"  b1={b1}: n={tot}, top nat={allc.most_common(5)}")

# registry CSV (unique matches only)
with open(os.path.join(OUT, 'face_texture_registry.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['pid', 'player_name', 'nat', 'matched_texture_name', 'byte1', 'byte0', 'byte4', 'byte7', 'byte10', 'byte14', 'hex17'])
    for pid, name, nat, tex, a in sorted(matches, key=lambda m: m[3]):
        w.writerow([pid, name, nat, tex, a[1], a[0], a[4], a[7], a[10], a[14], a.hex()])
print(f"\nwrote face_texture_registry.csv ({len(matches)} rows)")
