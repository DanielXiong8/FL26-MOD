# -*- coding: utf-8 -*-
"""extract_rosters.py - per-team effective rosters from the BUILT bundle.
Output: game_rosters.json {team_id: {"name": <en name>, "players": [[pid, name, ovr], ...]}}
"""
import json, os, struct
import UnityPy

BASE = r'D:\FL26_Mod\work\fc26_alignment'
BUNDLE = r'D:\FL26_Mod\build\gamedata_pl2.unity3d'

env = UnityPy.load(BUNDLE)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        b = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
        assets[d.m_Name] = b

# ---- Players ----
raw = assets['Players']
off = 8
ncnt, = struct.unpack_from('<H', raw, off); off += 2
for _ in range(ncnt):
    ln, = struct.unpack_from('<H', raw, off); off += 2 + ln * 2
pcnt, = struct.unpack_from('<I', raw, off); off += 4
players = {}
for _ in range(pcnt):
    pid, = struct.unpack_from('<I', raw, off); off += 4
    ln, = struct.unpack_from('<H', raw, off); off += 2
    nm = raw[off:off + ln * 2].decode('utf-16-le', errors='replace'); off += ln * 2
    fa, fb, fc, nat = struct.unpack_from('<HHHH', raw, off); off += 8
    b1, b16, b0 = raw[off], raw[off + 1], raw[off + 2]; off += 3
    attrs = list(raw[off:off + 17]); off += 17
    tail16, = struct.unpack_from('<H', raw, off); off += 2
    tail8 = raw[off]; off += 1
    year, = struct.unpack_from('<I', raw, off); off += 4
    players[pid] = {'name': nm, 'ovr': attrs[1], 'nat': nat, 'year': year}
print('players:', len(players))

# ---- ClubPlayer ----
cp = assets['ClubPlayer']
n1, = struct.unpack_from('<I', cp, 0)
teams = {}
for i in range(n1):
    tid, cnt = struct.unpack_from('<II', cp, 4 + i * 8)
    teams[tid] = cnt
off = 4 + n1 * 8
members = []
while off + 17 <= len(cp):
    tid, p, jersey, f2 = struct.unpack_from('<IIII', cp, off)
    members.append((tid, p, jersey))
    off += 17
print('members:', len(members), 'teams:', len(teams))

# ---- Teams + strings(EN) for team names ----
team_name = {}
if 'Teams' in assets:
    t = assets['Teams']
    # Teams csv: find team id -> name-key (col6/col7 per survey); reuse lenient scan
    try:
        txt = t.decode('utf-8', errors='replace')
        import re
        for line in txt.splitlines():
            parts = line.split(',')
            if len(parts) > 7 and parts[0].isdigit():
                team_name[int(parts[0])] = parts[6]
    except Exception as e:
        print('teams parse warn:', e)
names_en = {}
if 'strings' in assets:
    s = assets['strings']
    try:
        txt = s.decode('utf-8', errors='replace')
        import re
        for line in txt.splitlines():
            m = re.match(r'([^,]+),EN,(.*)$', line)
            if m:
                names_en[m.group(1)] = m.group(2)
    except Exception as e:
        print('strings parse warn:', e)

rosters = {}
for tid in teams:
    pls = [(p, players.get(p, {}).get('name', '?'), players.get(p, {}).get('ovr', 0), j)
           for (tt, p, j) in members if tt == tid]
    nkey = team_name.get(tid, '')
    rosters[tid] = {
        'key': nkey,
        'name': names_en.get(nkey, nkey),
        'players': sorted(pls, key=lambda x: x[3]),
    }
json.dump(rosters, open(os.path.join(BASE, 'game_rosters.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('rosters saved: %d teams' % len(rosters))
# sample
for tid in (20027, 20030, 20026):
    r = rosters.get(tid)
    if r:
        print(tid, r['name'], len(r['players']), 'players, e.g.', [p[1] for p in r['players'][:5]])
