# -*- coding: utf-8 -*-
"""clean_transfer_audit.py - for the 97 inject players, find EXISTING DB records that
are the same person (a transfer source), using surname-fragment + OVR-proximity +
nation (when known). High confidence only. Output: transfer_map.json + console.
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
man = json.load(open(BASE + r'\pl_update_manifest.json', encoding='utf-8'))

# nationality per real name (subset of the 97); used to gate common-surname matches
NAT = {
 'Bradley Barcola': 'France', 'Kostas Tsimikas': 'Greece', 'Ronald Araujo': 'Uruguay',
 'Julián Araujo': 'Mexico', 'Takehiro Tomiyasu': 'Japan', 'Ben Chilwell': 'England',
 'Brennan Johnson': 'Wales', 'Alejandro Garnacho': 'Argentina', 'Estêvão': 'Brazil',
 'Joël Veltman': 'Netherlands', 'Ismaïla Sarr': 'Senegal', 'Pascal Groß': 'Germany',
 'Kevin Schade': 'Germany', 'Kaoru Mitoma': 'Japan', 'Ferdi Kadıoğlu': 'Turkey',
 'Xavi Simons': 'Netherlands', 'Mohamed Salah': 'Egypt', 'Ousmane Diomande': 'Ivory Coast',
 'Daniel Muñoz': 'Colombia', 'David Raya': 'Spain', 'Gabriel Magalhães': 'Brazil',
}


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_accents(s).lower())


# index: surname-fragment(>=4) -> list of (team_display,league,pid,name,jersey,ovr,nat)
idx = {}
for tid, t in db['teams'].items():
    disp = t.get('display') or t.get('name_key')
    lg = t.get('league') or ''
    for p in t['roster']:
        fr = norm(p['name'])
        for i in range(len(fr) - 3):
            frag = fr[i:i + 5]
            idx.setdefault(frag, []).append(
                {'team': disp, 'league': lg, 'pid': p['pid'], 'name': p['name'],
                 'jersey': p['jersey'], 'ovr': p['attrs'][1], 'nat': p['nat'], 'src': p['name']})

transfers, injects = [], []
for e in man['inject']:
    real = e['name']
    rn = norm(real)
    surname = norm(real.split()[-1])
    best, bestsc = None, -1
    seen = set()
    for i in range(max(1, len(surname) - 4)):
        frag = surname[i:i + 5]
        for c in idx.get(frag, []):
            if c['pid'] in seen:
                continue
            seen.add(c['pid'])
            # surname overlap score
            so = SequenceMatcher(None, surname, norm(c['src'])).ratio()
            if so < 0.6:
                continue
            sc = so
            # OVR proximity
            if abs(c['ovr'] - e['ovr']) <= 12:
                sc += 0.3
            else:
                sc -= 0.3
            # nation gate (strong) if known and present
            want = NAT.get(real)
            if want:
                if c['nat'] and norm(c['nat']) == norm(want):
                    sc += 0.4
                else:
                    sc -= 0.2
            if sc > bestsc:
                bestsc, best = sc, c
    if best and bestsc >= 1.2:
        transfers.append({'real': real, 'club': e['club'], 'team_id': e['team_id'],
                          'ovr_target': e['ovr'], 'src': best, 'score': round(bestsc, 2)})
    else:
        injects.append(real)

print('=== TRANSFER AUDIT (high-confidence) ===')
for t in transfers:
    s = t['src']
    print('  %-22s -> src %-18s|%s ovr=%d (want %d) sc=%.2f' % (
        t['real'], s['name'], s['team'], s['ovr'], t['ovr_target'], t['score']))
print()
print('confirmed transfers: %d | true injects: %d' % (len(transfers), len(injects)))
json.dump({'transfers': transfers, 'injects': injects},
          open(BASE + r'\transfer_map.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
