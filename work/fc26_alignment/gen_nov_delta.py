# -*- coding: utf-8 -*-
"""gen_nov_delta.py - generate November squad-sync ops from compare2 report.

For each missing wiki player:
  - global fuzzy search across ALL game rosters
      * best at SAME team  (surname ratio>=0.82) -> RENAME card to real name
      * best at OTHER team (score>=2.2)          -> TRANSFER card to target club
      * nowhere                                  -> INJECT (real name, jersey, pos,
         ovr: dongqiudi > club median; nat: wiki row nat / Saudi foreign table / league default)
  - cap guard: teams projected >35 get REMOVE ops for lowest-OVR unmatched extras
Coaches are filtered (name adjacent to manager/coach in source text).
Merges ops into pl_plan.json (backup first). Output: nov_delta.json
"""
import json, os, re, sys, unicodedata, difflib, collections, statistics

BASE = r'D:\FL26_Mod\work\fc26_alignment'
NEW = os.path.join(BASE, 'wiki_nov')
sys.path.insert(0, BASE)
FIFA = {'GER':'Germany','ITA':'Italy','FRA':'France','BRA':'Brazil','ARG':'Argentina',
 'ESP':'Spain','ENG':'England','NED':'Netherlands','POR':'Portugal','BEL':'Belgium',
 'DEN':'Denmark','SWE':'Sweden','NOR':'Norway','SUI':'Switzerland','AUT':'Austria',
 'POL':'Poland','CZE':'Czech Republic','USA':'United States','JPN':'Japan',
 'KOR':'South Korea','MAR':'Morocco','SEN':'Senegal','NGA':'Nigeria','CIV':'Ivory Coast',
 'GHA':'Ghana','CMR':'Cameroon','ALG':'Algeria','TUN':'Tunisia','EGY':'Egypt',
 'COL':'Colombia','URU':'Uruguay','CHI':'Chile','PAR':'Paraguay','PER':'Peru',
 'ECU':'Ecuador','VEN':'Venezuela','MEX':'Mexico','CRC':'Costa Rica','AUS':'Australia',
 'TUR':'Turkey','GRE':'Greece','SRB':'Serbia','CRO':'Croatia','SVK':'Slovakia',
 'SVN':'Slovenia','BIH':'Bosnia and Herzegovina','ALB':'Albania','MKD':'North Macedonia',
 'ROU':'Romania','BUL':'Bulgaria','HUN':'Hungary','UKR':'Ukraine','RUS':'Russia',
 'ISR':'Israel','GEO':'Georgia','ARM':'Armenia','KEN':'Kenya','GAB':'Gabon',
 'COD':'DR Congo','ANG':'Angola','RSA':'South Africa','MLI':'Mali','BFA':'Burkina Faso',
 'GUI':'Guinea','GNB':'Guinea-Bissau','CPV':'Cape Verde','UZB':'Uzbekistan','IRQ':'Iraq',
 'KSA':'Saudi Arabia','IRN':'Iran','WAL':'Wales','SCO':'Scotland','IRL':'Republic of Ireland',
 'CAN':'Canada','PAN':'Panama','JAM':'Jamaica','HON':'Honduras','CGO':'Congo','LBY':'Libya',
 'FIN':'Finland','ISL':'Iceland','EST':'Estonia','LVA':'Latvia','LTU':'Lithuania',
 'KVX':'Kosovo','MNE':'Montenegro','MDA':'Moldova','UAE':'United Arab Emirates',
 'QAT':'Qatar','CHN':'China PR','IND':'India','THA':'Thailand','VIE':'Vietnam',
 'AUS2':'Australia','NZL':'New Zealand','PUR':'Puerto Rico','DOM':'Dominican Republic',
 'CUB':'Cuba','HAI':'Haiti','GUF':'French Guiana','MTN':'Mauritania','NIG':'Niger','BLR':'Belarus','CHE':'Switzerland','CHL':'Chile','CRI':'Costa_Rica','CUW':'Curacao',
 'EQG':'Equatorial_Guinea','GLP':'Guadeloupe','HKG':'CHINA_HONG_KONG','KAZ':'Kazakhstan','KOS':'Kosovo',
 'LCA':'Saint_Lucia','LUX':'Luxembourg','NCL':'New_Caledonia','NGR':'Nigeria','PRK':'North_Korea',
 'PRY':'Paraguay','SER':'Serbia','SLO':'Slovenia','SMN':'San_Marino','TGO':'Togo','TPE':'Chinese_Taipei',
 'VIN':'Saint_Vincent_and_the_Grenadines',
 'TCD':'Chad','SUD':'Sudan','ZAM':'Zambia','ZIM':'Zimbabwe','MOZ':'Mozambique',
 'ANG2':'Angola','BEN':'Benin','TOG':'Togo','GAM':'Gambia','SLE':'Sierra Leone',
 'LBR':'Liberia','GHA2':'Ghana','RWA':'Rwanda','UGA':'Uganda','TAN':'Tanzania',
 'BDI':'Burundi','ETH':'Ethiopia','SOM':'Somalia','DJI':'Djibouti','COM':'Comoros',
 'CPV2':'Cape Verde','SYR':'Syria','LBN':'Lebanon','JOR':'Jordan','PLE':'Palestine',
 'KUW':'Kuwait','BHR':'Bahrain','OMA':'Oman','YEM':'Yemen','AFG':'Afghanistan',
 'PAK':'Pakistan','BAN':'Bangladesh','SRI':'Sri Lanka','MAS':'Malaysia','SIN':'Singapore',
 'IDN':'Indonesia','PHI':'Philippines','MGL':'Mongolia','KGZ':'Kyrgyzstan',
 'TJK':'Tajikistan','TKM':'Turkmenistan','UZB2':'Uzbekistan','NEP':'Nepal',
 'CAM':'Cambodia','LAO':'Laos','MYA':'Myanmar','BHU':'Bhutan','BRU':'Brunei',
 'TAI':'Chinese Taipei','GUA':'Guatemala','SLV':'El Salvador','NCA':'Nicaragua',
 'CRC2':'Costa Rica','HON2':'Honduras','SUR':'Suriname','GUY':'Guyana','VEN2':'Venezuela',
 'BOL':'Bolivia','PAR2':'Paraguay','TRI':'Trinidad and Tobago','BAR':'Barbados',
 'FIJ':'Fiji','SOL':'Solomon Islands','TAH':'Tahiti','PNG':'Papua New Guinea'}  # noqa inline copy (importing plan_bulk has side effects)

BACKUP = os.path.join(BASE, 'pl_plan_20261103_bak.json')


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def toks(s):
    s = strip_acc(s).lower()
    s = re.sub(r"[^a-z\s\-]", ' ', s)
    out = []
    for part in s.split():
        out.extend([p for p in re.split(r'-+', part) if p])
    return [t for t in out if t not in ('al', 'el', 'bin', 'ibn')]


def ratio(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def match_score(gname, wname):
    g = toks(gname)
    w = toks(wname)
    if not g or not w:
        return 0.0
    if g == w:
        return 3.0
    best = 0.0
    for gi, wi in ((g[-1], w[-1]), (g[0], w[0])):
        sr = ratio(gi, wi)
        given_ok = bool((set(g) - {gi}) & (set(w) - {wi}))
        if gi == wi:
            best = max(best, 2.2 if not given_ok else 2.6)
        elif sr >= 0.85:
            best = max(best, 2.3 if given_ok else 2.0)
        elif sr >= 0.78:
            best = max(best, 1.9)
    common = set(g) & set(w)
    if len(common) >= 2:
        best = max(best, 2.2)
    elif common and max(len(t) for t in common) >= 5:
        best = max(best, 1.6)
    return best


def surname_ratio(gname, wname):
    g = toks(gname)
    w = toks(wname)
    if not g or not w:
        return 0.0
    return max(ratio(g[-1], w[-1]), ratio(g[0], w[0]))


# ---------- load ----------
compare = json.load(open(BASE + r'\nov_team_compare2.json', encoding='utf-8'))
rosters = json.load(open(BASE + r'\game_rosters.json', encoding='utf-8'))
plan = json.load(open(BASE + r'\pl_plan.json', encoding='utf-8'))
shutil_copy = None
import shutil
if not os.path.exists(BACKUP):
    shutil.copyfile(BASE + r'\pl_plan.json', BACKUP)
    print('plan backed up ->', BACKUP)
dqd = json.load(open(BASE + r'\dqd_abilities.json', encoding='utf-8'))
targets = json.load(open(BASE + r'\nov_target_pages.json', encoding='utf-8'))

# league default nation
LEAGUE_NAT = {'SaudiT': 'Saudi Arabia', 'CSL': 'China_PR', 'Super': 'Turkey',
              'PL': 'England', 'LaLiga': 'Spain', 'SerieA': 'Italy',
              'Bundesliga': 'Germany', 'Ligue1': 'France'}

# ---------- nat rows per page (name -> fifa code) ----------
def nat_rows(path):
    out = {}
    txt = open(path, encoding='utf-8').read()
    for m in re.finditer(r'\{\{[Ff]s2? ?player([^{}]*)\}\}', txt):
        body = m.group(1)
        nat = re.search(r'\|\s*nat(?:ional)?\s*=\s*([A-Za-z_]+)', body)
        nm = re.search(r'\|\s*name\s*=\s*([^|}]*)', body)
        if nat and nm:
            cn = re.search(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', nm.group(1))
            key = (cn.group(1) if cn else nm.group(1)).strip()
            out[key.lower()] = nat.group(1).strip()
    return out

# Saudi foreign players table: club -> {player: fifa}
saudi_txt = open(os.path.join(NEW, '2026–27 Saudi Pro League.txt'), encoding='utf-8').read()
i = saudi_txt.find('Foreign players')
ftab = {}
club_now = None
for line in saudi_txt[i:i + 40000].splitlines():
    m = re.match(r'^\|\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*$', line.strip())
    if m:
        club_now = m.group(1)
        continue
    if line.strip().startswith('|-'):
        continue
    for mm in re.finditer(r'\{\{flagicon\|([A-Za-z0-9]+)[^}]*\}\}\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', line):
        if club_now:
            ftab.setdefault(club_now, {})[mm.group(2).strip()] = mm.group(1)
print('saudi foreign table clubs:', len(ftab))

T8 = json.load(open(BASE + r'\league_map8.json', encoding='utf-8'))['Saudi']
saudi_club_titles = {v[0]: k for k, v in T8.items()}

tp_by_tid = {}
for _t, _v in targets.items():
    tp_by_tid[str(_v['tid'])] = {'title': _t, **_v}

# ---------- global index ----------
gidx = []
for tid, v in rosters.items():
    for (pid, nm, ovr, j) in v['players']:
        gidx.append({'pid': pid, 'tid': int(tid), 'name': nm, 'ovr': ovr, 'jersey': j})
print('global index:', len(gidx))


def is_coach(title, name):
    p = os.path.join(NEW, title.replace(':', '_') + '.txt')
    if not os.path.exists(p):
        return False
    txt = open(p, encoding='utf-8').read()
    for m in re.finditer(re.escape(name), txt):
        ctx = txt[max(0, m.start() - 150):m.start() + 150].lower()
        if re.search(r'manager|head coach|coach\b', ctx) and 'squad end' not in ctx:
            # only when outside the squad block is hard; manager rows live after squad end
            after_end = txt.find('{{football squad end}}')
            if after_end >= 0 and m.start() > after_end:
                return True
    return False


injects, renames, transfers, removes, skipped = [], [], [], [], []
seen_names = set()
projected = {int(tid): len(v['players']) for tid, v in rosters.items()}
used_jersey = {}
for tid, v in rosters.items():
    used_jersey[int(tid)] = set(j for (_, _, _, j) in v['players'])

for tid, v in sorted(compare.items()):
    league, club = v['league'], v['club']
    tid_i = int(tid)
    roster = rosters[tid]['players']
    team_ovrs = [p[2] for p in roster if p[2]]
    median_ovr = int(statistics.median(team_ovrs)) if team_ovrs else 68
    for mp in v['missing']:
        nm = mp['name']
        if nm.lower() in seen_names:
            continue
        seen_names.add(nm.lower())
        if is_coach(v['title'], nm):
            skipped.append({'club': club, 'name': nm, 'why': 'coach'})
            continue
        # global fuzzy search
        best_same, best_other = None, None
        for g in gidx:
            if g['tid'] == tid_i:
                s = match_score(g['name'], nm)
                sr = surname_ratio(g['name'], nm)
                if best_same is None or (s, sr) > (best_same[0], best_same[1]):
                    best_same = (s, sr, g)
            else:
                s = match_score(g['name'], nm)
                if best_other is None or s > best_other[0]:
                    best_other = (s, g)
        # classify
        if best_same and best_same[0] >= 1.9:
            g = best_same[2]
            gt, wt = toks(g['name']), toks(nm)
            sn_last = ratio(gt[-1], wt[-1]) if gt and wt else 0.0
            first_ok = (len(gt) == 1) or (gt[0][0] == wt[0][0]) or ratio(gt[0], wt[0]) >= 0.5
            if sn_last >= 0.85 and first_ok:
                renames.append({'pid': g['pid'], 'name': nm,
                                'old': g['name'], 'club': club, 'tid': tid_i})
                continue
            # else: falls through to inject/transfer checks below (no blind rename)
        if best_other and best_other[0] >= 2.3:
            g = best_other[1]
            if 10000 <= g['tid'] < 20000:   # national-team / classic cards never transfer
                skipped.append({'club': club, 'name': nm, 'why': 'src is national team'})
                continue
            # loan/parent guard: if the src club page still lists the player, keep him there
            src_info = tp_by_tid.get(str(g['tid']))
            if src_info:
                sp = os.path.join(NEW, src_info['title'].replace(':', '_') + '.txt')
                if os.path.exists(sp) and nm.lower() in open(sp, encoding='utf-8').read().lower():
                    skipped.append({'club': club, 'name': nm, 'why': 'src page still lists (loan?)'})
                    continue
            transfers.append({'pid': g['pid'], 'src_team': g['tid'], 'src_name': g['name'],
                              'dst_club': club, 'new_team': tid_i, 'jersey': mp.get('no') or 0,
                              'ovr': g['ovr'], 'real': nm})
            projected[tid_i] += 1
            projected[g['tid']] -= 1
            continue
        # INJECT
        nat_code = None
        p = os.path.join(NEW, v['title'].replace(':', '_') + '.txt')
        if os.path.exists(p):
            nat_code = nat_rows(p).get(nm.lower())
        nat_name = None
        if league == 'SaudiT':
            stitle = v['title'].replace('Template:', '').replace('Template_', '')
            # find saudi club page title via club key
            skey = saudi_club_titles.get(club)
            saudi_name = None
            if skey:
                for link, code in ftab.get(skey, {}).items():
                    if ratio(strip_acc(link).lower(), strip_acc(nm).lower()) >= 0.85:
                        saudi_name = code
                        break
                if nm.lower() in {k.lower() for k in ftab.get(skey, {})}:
                    saudi_name = ftab[skey][[k for k in ftab[skey] if k.lower() == nm.lower()][0]]
            nat_name = FIFA.get(saudi_name, 'Saudi Arabia') if saudi_name else 'Saudi Arabia'
        elif nat_code:
            nat_name = FIFA.get(nat_code) or (nat_code if nat_code[0].isupper() else None)
        if not nat_name:
            nat_name = LEAGUE_NAT.get(league, 'England')
        no = mp.get('no')
        jersey = no if (no and 1 <= no <= 99) else None
        uj = used_jersey.get(tid_i, set())
        if jersey is None or jersey in uj:
            jersey = next((j for j in range(2, 99) if j not in uj), 99)
        uj.add(jersey)
        dq = dqd.get(nm) or {}
        no_v = mp.get('no')
        ovr = dq.get('ovr') or (median_ovr if (no_v and no_v <= 25) else max(58, median_ovr - 8))
        birth = None
        if dq.get('dob'):
            birth = int(dq['dob'][:4])
        if not tid_i:
            skipped.append({'club': club, 'name': nm, 'why': 'no team id'})
            continue
        injects.append({'club': club, 'team_id': tid_i, 'name': nm, 'jersey': jersey,
                        'pos': mp.get('pos') or 'MF', 'ovr': int(ovr), 'birth': birth,
                        'nat': nat_name, 'src': league})
        projected[tid_i] += 1

# ---------- cap guard <= 35 ----------
for tid_i, size in sorted(projected.items()):
    if size <= 35:
        continue
    v = compare.get(str(tid_i))
    league = v['league'] if v else '?'
    extra = v['extra'] if v else []
    cand = sorted(extra, key=lambda e: e[2] or 0)
    for e in cand:
        if size <= 35:
            break
        removes.append({'team': tid_i, 'pid': e[0], 'name': e[1]})
        size -= 1
        projected[tid_i] -= 1
    if size > 35:
        print('WARN still over cap: tid', tid_i, size)

json.dump({'injects': injects, 'renames': renames, 'transfers': transfers,
           'removes': removes, 'skipped': skipped},
          open(BASE + r'\nov_delta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('\n=== NOV DELTA ===')
print('INJECT %d | RENAME %d | TRANSFER %d | REMOVE %d | skipped %d' % (
    len(injects), len(renames), len(transfers), len(removes), len(skipped)))
agg = collections.Counter(e['club'] for e in injects)
print('injects by club (top):', dict(agg.most_common(10)))
tid2lg = {str(v['tid']): v['league'] for v in targets.values() if v.get('tid')}
byl = collections.Counter(tid2lg.get(str(e['team_id']), '?') for e in injects)
print('injects by league:', dict(byl))
print('renames sample:', renames[:6])
print('transfers sample:', transfers[:6])
