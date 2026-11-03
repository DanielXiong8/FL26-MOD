# -*- coding: utf-8 -*-
"""analyze_wiki_diff.py - rebuild full old/new wikitext diff with section context,
keep squad-relevant changes for the 8 target leagues' pages.
Output: nov_squad_changes.json {page: {league, club, tid, changes: [{sec, dir, line}]}}
"""
import json, os, re, difflib

BASE = r'D:\FL26_Mod\work\fc26_alignment'
OLD = os.path.join(BASE, 'wiki')
NEW = os.path.join(BASE, 'wiki_nov')

# ---- page -> (league, club, tid) for target leagues ----
PAGES = {}
tp = json.load(open(BASE + r'\nov_target_pages.json', encoding='utf-8'))
for title, v in tp.items():
    PAGES[title] = (v['league'], v['club'], v['tid'])

PL = {'Arsenal': ('Arsenal FC', 20030), 'Liverpool': ('Liverpool F.C.', 20027),
      'Chelsea': ('Chelsea F.C.', 20028), 'Tottenham': ('Tottenham Hotspur F.C.', 20029),
      'Newcastle': ('Newcastle United F.C.', 20037), 'ManCity': ('Manchester City F.C.', 20026),
      'ManUnited': ('Manchester United F.C.', 20031), 'Bournemouth': ('A.F.C. Bournemouth', 20046),
      'AstonVilla': ('Aston Villa F.C.', 20039), 'Brentford': ('Brentford F.C.', 20036),
      'Brighton': ('Brighton & Hove Albion F.C.', 20035), 'CrystalPalace': ('Crystal Palace F.C.', 20038),
      'Everton': ('Everton F.C.', 20041), 'Fulham': ('Fulham F.C.', 20367),
      'Coventry': ('Coventry City F.C.', 20324), 'Ipswich': ('Ipswich Town F.C.', 20398),
      'HullCity': ('Hull City A.F.C.', 20313), 'NottinghamForest': ('Nottingham Forest F.C.', 20050),
      'Sunderland': ('Sunderland A.F.C.', 20311), 'WestHam': ('West Ham United F.C.', 20032)}
for club, (title, tid) in PL.items():
    PAGES[title] = ('PL', club, tid)

LEAGUE_PAGES = {'2026–27 Süper Lig': ('SuperLig', '*', None),
                '2026–27 Saudi Pro League': ('SaudiPL', '*', None),
                '2026 Chinese Super League': ('CSL', '*', None)}
for t, v in LEAGUE_PAGES.items():
    PAGES[t] = v

# resolve actual cached filenames (old cache names may differ slightly)
cache_old = {f[:-4]: f for f in os.listdir(OLD) if f.endswith('.txt')}

def resolve(title):
    if title in cache_old:
        return cache_old[title]
    t2 = title.replace('2026-27', '2026–27')
    if t2 in cache_old:
        return cache_old[t2]
    # fuzzy: ignore dots/spases
    norm = re.sub(r'[ .]', '', title.lower())
    for f in cache_old:
        if re.sub(r'[ .]', '', f.lower()) == norm:
            return f
    return None

SQUAD_PAT = re.compile(r'\{\{\s*(Fs player|Football squad player|Fs player2|Fs player|no2)', re.I)

out = {}
missing = []
for title, (lg, club, tid) in PAGES.items():
    f_old = resolve(title)
    if not f_old:
        missing.append(title)
        continue
    p_old = os.path.join(OLD, f_old)
    p_new = os.path.join(NEW, title.replace('/', '_'))
    if not os.path.exists(p_new):
        p_new = os.path.join(NEW, f_old)
    if not os.path.exists(p_new):
        missing.append(title + ' [no fresh copy]')
        continue
    old = open(p_old, encoding='utf-8').read().splitlines()
    new = open(p_new, encoding='utf-8').read().splitlines()

    def section_of(lines, ln):
        sec = '?'
        for i in range(min(ln, len(lines))):
            if lines[i].strip().startswith('==') and lines[i].strip().endswith('=='):
                sec = lines[i].strip().strip('=').strip()
        return sec

    changes = []
    for line in difflib.unified_diff(old, new, lineterm='', n=0):
        if line.startswith('+++') or line.startswith('---') or line.startswith('@'):
            continue
        body = line[1:]
        if not SQUAD_PAT.search(body) and 'name=' not in body:
            continue
        src = new if line.startswith('+') else old
        # find approx position of this line in src for section lookup
        pos = next((i for i, l in enumerate(src) if l.strip() == body.strip()), 0)
        sec = section_of(src, pos)
        changes.append({'sec': sec, 'dir': 'in' if line.startswith('+') else 'out',
                        'line': body.strip()[:220]})
    if changes:
        out[title] = {'league': lg, 'club': club, 'tid': tid, 'changes': changes}

print('pages checked: %d | with squad changes: %d | missing: %d' % (len(PAGES), len(out), len(missing)))
for m in missing:
    print('  missing:', m)
json.dump(out, open(os.path.join(BASE, 'nov_squad_changes.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
# summary by league
import collections
cnt = collections.Counter(v['league'] for v in out.values())
print('by league:', dict(cnt))
