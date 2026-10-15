# -*- coding: utf-8 -*-
"""alias_match.py - per PL club, fuzzy-match CURRENT game roster (obfuscated name)
to the TARGET 2026-27 squad (real name). Builds the step-1 alias table
(game_name -> real_name). Outputs alias_proposal.json with confidence so low ones
can be hand-corrected.
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
sq = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))

PL = {
 'Arsenal':20030,'Liverpool':20027,'Chelsea':20028,'Tottenham':20029,'Newcastle':20037,
 'ManCity':20026,'ManUnited':20031,'Bournemouth':20046,'AstonVilla':20039,'Brentford':20036,
 'Brighton':20035,'CrystalPalace':20038,'Everton':20041,'Fulham':20367,'Coventry':20324,
 'Ipswich':20398,'HullCity':20313,'NottinghamForest':20050,'Sunderland':20311,'WestHam':20032
}


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_accents(s).lower())


# surname = last token (most distinctive)
def surnames(s):
    parts = re.split(r'[\s\-]', s.strip())
    return [p for p in parts if p]


def best_match(gname, targets):
    """targets: list of real names. return (real, score)."""
    gn = norm(gname)
    g_surn = [norm(x) for x in surnames(gname)]
    best, bests = None, -1
    for real in targets:
        rn = norm(real)
        r_surn = [norm(x) for x in surnames(real)]
        s = SequenceMatcher(None, gn, rn).ratio()
        # surname bonus
        if any(g in rn or (g and g == r) for g in g_surn for r in r_surn):
            s += 0.15
        # containment bonus
        if (gn in rn or rn in gn) and min(len(gn), len(rn)) >= 4:
            s += 0.1
        s += 0.05
        if s > bests:
            bests, best = s, real
    return best, bests


out = {}
for club, tid in PL.items():
    team = db['teams'].get(str(tid), {})
    game = [(p['pid'], p['name'], p['jersey'], p['attrs'][1]) for p in team.get('roster', [])]
    targets = []
    for pos in ('GK', 'DF', 'MF', 'FW'):
        for num, nm in sq.get(club, {}).get(pos, []) or []:
            targets.append((nm, int(num) if str(num).isdigit() else 0, pos))
    tnames = [t[0] for t in targets]
    rows = []
    used = set()
    for pid, gname, jersey, ovr in game:
        real, score = best_match(gname, tnames)
        rows.append({'pid': pid, 'game_name': gname, 'jersey': jersey, 'ovr': ovr,
                     'match': real, 'score': round(score, 3),
                     'conf': 'HI' if score >= 0.82 else ('MED' if score >= 0.70 else 'LO')})
    out[club] = {'tid': tid, 'rows': rows,
                 'target_count': len(targets), 'game_count': len(game)}
    nlo = sum(1 for r in rows if r['conf'] == 'LO')
    nmed = sum(1 for r in rows if r['conf'] == 'MED')
    print('%-16s game=%d target=%d  LO=%d MED=%d' % (club, len(game), len(targets), nlo, nmed))
    for r in rows:
        if r['conf'] != 'HI':
            print('   %-6s %-20s -> %-24s (%.3f)' % (r['conf'], r['game_name'], r['match'], r['score']))

json.dump(out, open(BASE + r'\alias_proposal.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nwrote alias_proposal.json')
