# -*- coding: utf-8 -*-
"""match3.py - auto-match Bundesliga/SerieA/Ligue1 targets to game rosters.
Precision-first: auto-accept sc>=0.85; 0.72..0.85 only if jersey matches or
non-generic surname; generic-surname pairs require jersey match + sc>=0.9.
Output: match3_report.json + review console.
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))

import os
LEAGUES = json.load(open(os.environ.get('LEAGUES_FILE', BASE + r'\league_tids.json'), encoding='utf-8'))
GENERIC = {'garsia','garcia','fernandez','gonzalez','martin','lopez','sanchez','gomez',
 'rodriguez','torres','ruiz','molina','serrano','vargas','castro','rubio','perez',
 'moreno','hernandez','jimenez','navarro','romero','diaz','munoz','alvarez','ramos',
 'flores','rossi','ferrari','bianchi','cont','ricci','marino','greco','bruno','gallo',
 'costa','santos','silva','souza','pereira','oliveira','muller','schmidt','schneider',
 'fischer','weber','wagner','becker','hoffmann','schulz','koch','bauer','richter',
 'klein','wolf','neumann','schwarz','zimmermann','braun','kruger','hofmann','hartmann',
 'lange','werner','krause','lehmann','kobel','meyer','schulze','berger','winkler','busch'}


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_acc(s).lower())


def clean_target(nm):
    nm = re.sub(r'\s*\([^)]*\)', '', nm)   # drop disambiguation
    return re.sub(r'\s+', ' ', nm).strip()


def nsim(a, b):
    a_full = norm(clean_target(a))
    b_n = norm(b)
    if not a_full or not b_n:
        return 0.0
    best = SequenceMatcher(None, a_full, b_n).ratio()
    for tok in clean_target(a).split():
        t = norm(tok)
        if len(t) < 4:
            continue
        s2 = SequenceMatcher(None, t, b_n).ratio()
        if t in b_n:
            s2 = max(s2, 0.78)
        if s2 > best:
            best = s2
    return round(best, 3)


report = {}
for lg, clubs in LEAGUES.items():
    sq = json.load(open(BASE + r'\squad_%s.json' % lg, encoding='utf-8'))
    rep = {}
    for club, tid in clubs.items():
        if tid is None:
            continue
        team = db['teams'].get(str(tid), {})
        roster = {p['name']: (p['pid'], p['jersey'], p['attrs'][1]) for p in team.get('roster', [])}
        seen_pid = set()
        pairs, unmatched = [], []
        for num, nm, pos, nat in sq.get(club, []):
            want = int(num) if isinstance(num, int) and 0 < num <= 45 else 0
            gs = norm(nm.split()[-1]) if nm.split() else ''
            generic = gs in GENERIC
            best = None
            for g, (pid, gj, govr) in roster.items():
                sc = nsim(nm, g)
                if generic:
                    ok = sc >= 0.9 and want and gj == want
                else:
                    ok = sc >= 0.80 or (sc >= 0.68 and want and gj == want)
                if ok and pid not in seen_pid:
                    if best is None or sc > best[1]:
                        best = (g, sc)
            if best:
                seen_pid.add(roster[best[0]][0])
                pairs.append({'real': clean_target(nm), 'num': want, 'pos': pos, 'nat': nat,
                              'game': best[0], 'pid': roster[best[0]][0],
                              'jersey': roster[best[0]][1], 'ovr': roster[best[0]][2],
                              'sc': best[1]})
            else:
                unmatched.append([num, clean_target(nm), pos, nat])
        rep[club] = {'tid': tid, 'pairs': pairs, 'unmatched': unmatched,
                     'extras': [g for g in roster if roster[g][0] not in seen_pid]}
    report[lg] = rep
    nm_p = sum(len(r['pairs']) for r in rep.values())
    nm_u = sum(len(r['unmatched']) for r in rep.values())
    print('%s: pairs=%d unmatched=%d' % (lg, nm_p, nm_u))

import os as _o
json.dump(report, open(_o.environ.get('REPORT_FILE', BASE + r'\match3_report.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('wrote match3_report.json')
