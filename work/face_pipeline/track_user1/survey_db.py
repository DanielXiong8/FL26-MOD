# -*- coding: utf-8 -*-
# survey_db.py - FULL survey of the game database: teams, leagues, players,
# rosters, attributes. Output: db_survey.json + console summary.
import csv, io, json, struct, zipfile
import UnityPy

APK = r'D:\FL26_Mod\build\base_debuggable2.apk'
OUT = r'D:\FL26_Mod\work\db_survey.json'

# ---- extract gamedata TextAssets ----
with zipfile.ZipFile(APK) as z:
    open(r'D:\FL26_Mod\build\db_survey_gamedata.unity3d', 'wb').write(
        z.read('assets/bundles/gamedata.unity3d'))
env = UnityPy.load(r'D:\FL26_Mod\build\db_survey_gamedata.unity3d')
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        assets[d.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
print('TextAssets:', len(assets))

# ---- strings (EN/ZH_CN) ----
loc = {}
rdr = csv.reader(assets['strings'].decode('utf-8', errors='replace').split('\r\n'))
hdr = next(rdr)
i_en, i_zh = hdr.index('EN'), hdr.index('ZH_CN')
for r in rdr:
    if len(r) > max(i_en, i_zh) and r[0]:
        loc[r[0]] = (r[i_en], r[i_zh])
print('strings keys:', len(loc))

# ---- Teams ----
teams = {}
for row in csv.reader(assets['Teams'].decode('utf-8', errors='replace').split('\r\n')):
    if not row or not row[0].strip().isdigit():
        continue
    tid = int(row[0])
    nk = row[1] if len(row) > 1 else ''
    if nk in ('System', 'AllStar', 'SpecialPlayer', 'Duplicates', 'International'):
        continue
    def L(key):
        v = loc.get(key)
        return (v[1] or v[0]) if v else key
    is_nat = nk.startswith('Str_National')
    if is_nat:
        league_key = 'National'
        league = 'National Teams'
        display = L(nk) if nk in loc else nk.replace('Str_National_', '').replace('_', ' ')
    else:
        comp = row[6] if len(row) > 6 else ''
        league_key = comp
        league = L(comp) if comp in loc else comp.replace('CompName_', '')
        full = row[7].replace('Real_', '') if len(row) > 7 and row[7] else ''
        display = L(full) if full in loc else full.replace('_', ' ')
    teams[tid] = {'id': tid, 'name_key': nk, 'display': display,
                  'league': league, 'league_key': league_key, 'national': is_nat}
print('teams:', len(teams))

# ---- Players (plyrcsv0) ----
raw = assets['Players']
off = 8
ncnt, = struct.unpack_from('<H', raw, off); off += 2
nations = []
for _ in range(ncnt):
    ln, = struct.unpack_from('<H', raw, off); off += 2
    nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
pcnt, = struct.unpack_from('<I', raw, off); off += 4
players = {}
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
    players[pid] = {'pid': pid, 'name': name, 'nat': nations[nat] if nat < len(nations) else nat,
                    'attrs': attrs, 'fa': fa, 'fb': fb, 'fc': fc}
print('players:', len(players))

# ---- ClubPlayer (sec1 counts + sec2 memberships) ----
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
    sec2.append({'team': tid, 'pid': p, 'jersey': f1})
    off += 17
print('sec2 memberships:', len(sec2), '| sec1 teams:', len(sec1))

# ---- assemble ----
from collections import defaultdict
by_team = defaultdict(list)
for m in sec2:
    by_team[m['team']].append(m)

leagues = defaultdict(list)
for tid, t in teams.items():
    leagues[t['league']].append(tid)

survey = {'leagues': {}, 'teams': {}, 'players_total': len(players)}
for lg, tids in sorted(leagues.items()):
    real = [t for t in tids if teams[t]['national'] is False and not teams[t]['display'].startswith('National')]
    survey['leagues'][lg] = {'teams': len(tids), 'club_teams': len(real),
                             'team_ids': sorted(tids)[:400]}
for tid, t in teams.items():
    roster = []
    for m in by_team.get(tid, []):
        p = players.get(m['pid'])
        if p:
            roster.append({'pid': m['pid'], 'name': p['name'], 'jersey': m['jersey'],
                           'nat': p['nat'], 'attrs': p['attrs']})
    survey['teams'][tid] = {**t, 'roster_count_sec1': sec1.get(tid, 0),
                            'roster': roster}

json.dump(survey, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved', OUT)

# ---- summary ----
print('\n=== LEAGUES (by club team count) ===')
for lg in sorted(survey['leagues'], key=lambda k: -survey['leagues'][k]['club_teams'])[:30]:
    print('  %-45s teams=%d' % (lg[:45], survey['leagues'][lg]['club_teams']))
print('total leagues:', len(survey['leagues']), '| total teams:', len(teams),
      '| total players:', len(players), '| total memberships:', len(sec2))

# Liverpool
liv = [tid for tid, t in teams.items() if 'Liverpool' in t['display'] or 'Liverpool' in t.get('name_key', '')]
for tid in liv:
    t = survey['teams'][tid]
    print('\n=== %s (id %d, league: %s) roster %d ===' % (t['display'], tid, t['league'], len(t['roster'])))
    for p in sorted(t['roster'], key=lambda x: x['jersey']):
        print('  #%-3d %-25s nat=%-12s attrs=%s' % (p['jersey'], p['name'][:25], str(p['nat'])[:12], p['attrs'][:8]))