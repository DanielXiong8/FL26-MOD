# -*- coding: utf-8 -*-
"""audit_twins.py - for every player we planned to INJECT, search the WHOLE game DB
for an existing record of the same real person (legalized spellings included).
Hits mean: do NOT inject a new record; TRANSFER the existing pid instead.
Outputs: audit_twins_report.json + console table for manual review.
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
man = json.load(open(BASE + r'\pl_update_manifest.json', encoding='utf-8'))


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_accents(s).lower())


idx = {}
for tid, t in db['teams'].items():
    disp = t.get('display') or t.get('name_key') or ''
    lg = t.get('league') or ''
    for p in t['roster']:
        idx.setdefault(norm(p['name']), []).append({
            'tid': tid, 'team': disp, 'league': lg, 'pid': p['pid'],
            'game_name': p['name'], 'jersey': p['jersey'], 'nat': p['nat'],
            'ovr': p['attrs'][1]})


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


SURNAME_EXTRA = {}  # manual aliases: inject-name -> normalized game surname fragments
# known pure-legalization cases already handled in KNOWN_PAIRS stay matched; here we
# hunt CROSS-CLUB twins (transfers) + any remaining same-club miss.

rows = []
for e in man['inject']:
    q = norm(e['name'])
    cands = []
    for nm, lst in idx.items():
        if not nm:
            continue
        sc = sim(q, nm)
        cont = (q in nm or nm in q) and min(len(q), len(nm)) >= 5
        if sc >= 0.60 or cont:
            for rec in lst:
                cands.append((round(sc, 3), cont, rec))
    # dedupe by pid keeping best score
    best = {}
    for sc, cont, rec in cands:
        key = rec['pid']
        if key not in best or (sc, cont) > (best[key][0], best[key][1]):
            best[key] = (sc, cont, rec)
    top = sorted(best.values(), key=lambda x: (-x[0], -x[1]))[:5]
    rows.append({'club': e['club'], 'team_id': e['team_id'], 'real_name': e['name'],
                 'pos': e['pos'], 'jersey': e['jersey'], 'ovr': e['ovr'], 'cands': top})

print('=== INJECT-TWIN AUDIT: %d injected players ===' % len(rows))
strong, weak = [], []
for r in rows:
    tl = '%-16s %-24s' % (r['club'], r['real_name'])
    if not r['cands']:
        print('%s  NO CANDIDATE (truly new to DB)' % tl)
        continue
    sc, cont, rec = r['cands'][0]
    tag = 'STRONG' if (sc >= 0.74 or cont) else 'weak'
    print('%s  %s  best=%.3f%s  %s|%s #%s pid=%s nat=%s ovr=%s' % (
        tl, tag, sc, '*' if cont else ' ', rec['team'], rec['league'], rec['jersey'],
        rec['pid'], rec['nat'], rec['ovr']))
    if len(r['cands']) > 1:
        for sc2, cont2, rec2 in r['cands'][1:3]:
            print('%s            alt=%.3f%s  %s|%s #%s pid=%s' % (
                ' ' * len(tl), sc2, '*' if cont2 else ' ', rec2['team'], rec2['league'],
                rec2['jersey'], rec2['pid']))
    (strong if tag == 'STRONG' else weak).append(r)

print()
print('STRONG (likely same person exists in DB elsewhere -> convert to transfer): %d' % len(strong))
print('weak (manual check): %d' % len(weak))
print('none: %d' % (len(rows) - len(strong) - len(weak)))
json.dump(rows, open(BASE + r'\audit_twins_report.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
