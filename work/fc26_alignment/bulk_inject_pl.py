# -*- coding: utf-8 -*-
# bulk_inject_pl.py - inject the 97 missing PL players into gamedata.
# Reuses the DEVICE-PROVEN record formats (plyrcsv0 + ClubPlayer 17B).
# Output: gamedata_pl.unity3d (new bundle) + verification re-parse.
import io, json, os, struct, shutil, zipfile
import UnityPy

BASE = r'D:\FL26_Mod\work\fc26_alignment'
SRC_GD = r'D:\FL26_Mod\build\db_survey_gamedata.unity3d'
OUT_GD = r'D:\FL26_Mod\build\gamedata_pl.unity3d'
manifest = json.load(open(BASE + r'\pl_update_manifest.json', encoding='utf-8'))
squad = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))

env = UnityPy.load(SRC_GD)
assets = {}
objs = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        b = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
        assets[d.m_Name] = b
        objs[d.m_Name] = obj

# ---- parse Players ----
raw = assets['Players']
off = 8
ncnt, = struct.unpack_from('<H', raw, off); off += 2
nations = []
for _ in range(ncnt):
    ln, = struct.unpack_from('<H', raw, off); off += 2
    nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
pcnt, = struct.unpack_from('<I', raw, off); off += 4
recs = []
for _ in range(pcnt):
    pid, = struct.unpack_from('<I', raw, off); off += 4
    ln, = struct.unpack_from('<H', raw, off); off += 2
    name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    fa, fb, fc, nat = struct.unpack_from('<HHHH', raw, off); off += 8
    b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
    attrs = list(raw[off:off+17]); off += 17
    tail16, = struct.unpack_from('<H', raw, off); off += 2
    tail8 = raw[off]; off += 1
    year, = struct.unpack_from('<I', raw, off); off += 4
    recs.append({'pid': pid, 'name': name, 'fa': fa, 'fb': fb, 'fc': fc, 'nat': nat,
                 'b1': b1, 'b16': b16, 'b0': b0, 'attrs': attrs,
                 'tail16': tail16, 'tail8': tail8, 'year': year})
max_pid = max(r['pid'] for r in recs)
print('players: %d, max pid %d, nations %d' % (len(recs), max_pid, len(nations)))

# ---- parse ClubPlayer ----
cp = assets['ClubPlayer']
n1, = struct.unpack_from('<I', cp, 0)
sec1 = {}
for i in range(n1):
    tid, cnt = struct.unpack_from('<II', cp, 4 + i*8)
    sec1[tid] = cnt
sec2 = []
off = 4 + n1*8
while off + 17 <= len(cp):
    tid, p, f1, f2 = struct.unpack_from('<IIII', cp, off)
    sec2.append({'team': tid, 'pid': p, 'jersey': f1, 'f2': f2, 'f3': cp[off+16]})
    off += 17
print('clubplayer: sec1 %d teams, sec2 %d memberships' % (len(sec1), len(sec2)))

# ---- nation lookup ----
def nat_idx(name):
    for i, n in enumerate(nations):
        if n.lower() == name.lower():
            return i
    return 0
NAT_OVERRIDE = {'Vitezslav Jaros': 'Czech Republic', 'Harvey Davies': 'England',
 'Jeremy Jacquet': 'France', 'Kostas Tsimikas': 'Greece', 'Ronald Araujo': 'Uruguay',
 'Luke Chambers': 'England', 'James McConnell': 'England', 'Victor Munoz': 'Spain',
 'Bradley Barcola': 'France', 'Lewis Koumas': 'Wales', 'Jayden Danns': 'England',
 'Mike Penders': 'Belgium', 'Teddy Sharman-Lowe': 'England', 'Marco Palestra': 'Italy',
 'Valentin Barco': 'Argentina', 'Maxence Lacroix': 'France', 'Geovany Quenda': 'Portugal',
 'Estêvão': 'Brazil', 'David Raya': 'Spain', 'Tommy Setford': 'England',
 'Zion Suzuki': 'Japan', 'Alejandro Garnacho': 'Argentina', 'António Silva': 'Portugal',
 'Julián Araujo': 'Mexico', 'Edson Álvarez': 'Mexico', 'Joël Veltman': 'Netherlands',
 'Ousmane Diomande': 'Ivory Coast', 'Daniel Muñoz': 'Colombia', 'Ibrahim Sangaré': 'Ivory Coast',
 'Ismaïla Sarr': 'Senegal', 'Cheick Doucouré': 'Mali', 'Daichi Kamada': 'Japan',
 'Takehiro Tomiyasu': 'Japan', 'Óscar Mingueza': 'Spain', 'Darío Osorio': 'Chile',
 'Jørgen Strand Larsen': 'Norway', 'Yéremy Pino': 'Spain', 'Dwight McNeil': 'England',
 'Hugo Larsson': 'Sweden', 'Sander Berge': 'Norway', 'Antonee Robinson': 'United States',
 'Bernd Leno': 'Germany', 'Joachim Andersen': 'Denmark', 'Manuel Ángel': 'Spain',
 'César Palacios': 'Spain', 'Gonzalo García': 'Spain', 'Ryan Sessegnon': 'England',
 'Emile Smith Rowe': 'England', 'Alex Iwobi': 'Nigeria', 'Alex Borto': 'United States',
 'Mamadou Sangaré': 'Mali', 'Kim Ji-Soo': 'Korea Republic', 'Kevin Schade': 'Germany',
 'Pascal Struijk': 'Netherlands', 'Bart Verbruggen': 'Netherlands', 'Pascal Groß': 'Germany',
 'Kaoru Mitoma': 'Japan', 'Ferdi Kadıoğlu': 'Turkey', 'Lewis Dunk': 'England',
 'Joël Piroe': 'Netherlands', 'Manor Solomon': 'Israel', 'Maxwel Cornet': 'Ivory Coast',
 'Arne Engels': 'Belgium', 'Taty Castellanos': 'Argentina', 'Jarrod Bowen': 'England',
 'Mads Hermansen': 'Denmark', 'Alphonse Areola': 'France', 'Morato': 'Brazil',
 'Konstantinos Mavropanos': 'Greece', 'Tomáš Souček': 'Czech Republic',
 'Maximilian Kilman': 'England', 'Adama Boiro': 'Spain'}

# ---- template attrs per club+pos: use a matched teammate's attrs ----
game_by_name = {r['name']: r for r in recs}
def template_for(club, pos, tid):
    cands = [m for m in manifest['ovr_update'] if m['club'] == club]
    for m in cands:
        gname = m['game_name']
        for key, wl in squad.get(club, {}).items():
            if str(key).startswith('_') or key == 'X':
                continue
            for item in wl:
                if item[1] == m['real_name'] and key == pos and gname in game_by_name:
                    return game_by_name[gname]['attrs']
    # fallback: any first roster player of that team
    for p in sec2:
        if p['team'] == tid:
            src = next((r for r in recs if r['pid'] == p['pid']), None)
            if src:
                return src['attrs']
    return [70] * 17

# ---- apply FC26 OVR corrections (byte[1]) ----
ovr_fixed = 0
for u in manifest['ovr_update']:
    if 'ovr_fc26' not in u:
        continue
    for r in recs:
        if r['pid'] and r['name'] == u['game_name']:
            # verify club membership to avoid wrong-club same-name hits
            in_club = any(p['team'] == u['team_id'] and p['pid'] == r['pid'] for p in sec2)
            if in_club and r['attrs'][1] != u['ovr_fc26']:
                r['attrs'][1] = u['ovr_fc26']
                ovr_fixed += 1
            break
print('OVR corrections applied: %d' % ovr_fixed)

# ---- inject ----
new_recs, new_cp = [], []
pid = max_pid
JERSEY_USED = {}
for tid, cnt in sec1.items():
    JERSEY_USED[tid] = set(p['jersey'] for p in sec2 if p['team'] == tid)
added = 0
for e in manifest['inject']:
    pid += 1
    tid = e['team_id']
    nat = nat_idx(NAT_OVERRIDE.get(e['name'], 'England'))
    attrs = list(template_for(e['club'], e['pos'], tid))
    attrs[1] = e['ovr']
    jersey = e['jersey']
    if jersey <= 0 or jersey in JERSEY_USED.get(tid, set()):
        jersey = next(j for j in range(2, 99) if j not in JERSEY_USED.get(tid, set()))
    JERSEY_USED.setdefault(tid, set()).add(jersey)
    rec = {'pid': pid, 'name': e['name'], 'fa': 0, 'fb': 0, 'fc': 0, 'nat': nat,
           'b1': 14, 'b16': 0, 'b0': 6, 'attrs': attrs, 'tail16': 0, 'tail8': 0, 'year': 2026}
    new_recs.append(rec)
    next((p for p in sec2 if False), None)
    sec2.append({'team': tid, 'pid': pid, 'jersey': jersey, 'f2': 6912, 'f3': 0})
    sec1[tid] = sec1.get(tid, 0) + 1
    e['assigned_pid'] = pid
    e['assigned_jersey'] = jersey
    added += 1
print('injected %d players' % added)

# ---- serialize ----
out = io.BytesIO()
out.write(b'plyrcsv0')
out.write(struct.pack('<H', len(nations)))
for n in nations:
    nb = n.encode('utf-16-le', errors='replace')
    out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
allr = recs + new_recs
out.write(struct.pack('<I', len(allr)))
for r in allr:
    out.write(struct.pack('<I', r['pid']))
    nb = r['name'].encode('utf-16-le', errors='replace')
    out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
    out.write(struct.pack('<HHHH', r['fa'], r['fb'], r['fc'], r['nat']))
    out.write(bytes([r['b1'], r['b16'], r['b0']]))
    out.write(bytes(r['attrs']))
    out.write(struct.pack('<H', r['tail16']))
    out.write(bytes([r['tail8']]))
    out.write(struct.pack('<I', r['year']))
players_raw = out.getvalue()

out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1.items():
    out.write(struct.pack('<II', tid, cnt))
for r in sec2:
    out.write(struct.pack('<IIII', r['team'], r['pid'], r['jersey'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()

# ---- write the new bundle ----
shutil.copyfile(SRC_GD, OUT_GD)
env2 = UnityPy.load(OUT_GD)
n_written = 0
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'Players':
            d.m_Script = players_raw.decode('utf-8', errors='surrogateescape')
            d.save(); n_written += 1
        elif d.m_Name == 'ClubPlayer':
            d.m_Script = clubplayer_raw.decode('utf-8', errors='surrogateescape')
            d.save(); n_written += 1
with open(OUT_GD, 'wb') as f:
    f.write(env2.file.save())
print('bundle written: %s (%d assets patched)' % (OUT_GD, n_written))

json.dump(manifest, open(BASE + r'\pl_update_manifest.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---- verify: re-parse ----
env3 = UnityPy.load(OUT_GD)
for obj in env3.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'Players':
            raw = d.m_Script
            raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
            off2 = 8
            nc2, = struct.unpack_from('<H', raw, off2); off2 += 2 + sum(2 + 0 for _ in range(0))
            for _ in range(nc2):
                ln, = struct.unpack_from('<H', raw, off2); off2 += 2 + ln*2
            pc2, = struct.unpack_from('<I', raw, off2)
            print('VERIFY Players: %d (was %d, +%d)' % (pc2, pcnt, pc2 - pcnt))
        if d.m_Name == 'ClubPlayer':
            raw = d.m_Script
            raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
            n1b, = struct.unpack_from('<I', raw, 0)
            body = len(raw) - (4 + n1b*8)
            print('VERIFY ClubPlayer: sec2 records %d (was %d)' % (body // 17, len(sec2) - added))
print('DONE. New bundle: build/gamedata_pl.unity3d')
