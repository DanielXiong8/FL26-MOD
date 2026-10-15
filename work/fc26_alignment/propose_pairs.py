# -*- coding: utf-8 -*-
"""propose_pairs.py - for ALL 20 PL clubs, propose missing-target <-> obfuscated-roster
pairs (same-club match-misses) AND cross-club (intra-PL transfer) pairs.
Loose recall, human verifies. Output: proposals.json + console review list.
"""
import json, re, unicodedata
from difflib import SequenceMatcher

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
sq = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))

PL = {
 'Arsenal':20030,'Liverpool':20027,'Chelsea':20028,'Tottenham':20029,'Newcastle':20037,
 'ManCity':20026,'ManUnited':20031,'Bournemouth':20046,'AstonVilla':20039,'Brentford':20036,
 'Brighton':20035,'CrystalPalace':20038,'Everton':20041,'Fulham':20367,'Coventry':20324,
 'Ipswich':20398,'HullCity':20313,'NottinghamForest':20050,'Sunderland':20311,'WestHam':20032
}


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    return re.sub(r'[^a-z]', '', strip_acc(s).lower())


def nsim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    s = SequenceMatcher(None, a, b).ratio()
    if (a in b or b in a) and min(len(a), len(b)) >= 4:
        s += 0.15
    # surname token similarity
    sa, sb = a.split()[-1] if a.split() else '', b.split()[-1] if b.split() else ''
    if sa and sb and SequenceMatcher(None, sa, sb).ratio() > 0.8:
        s += 0.1
    return round(s, 3)


out = {}
for club, tid in PL.items():
    team = db['teams'].get(str(tid), {})
    roster = {p['name']: (p['pid'], p['jersey'], p['attrs'][1]) for p in team.get('roster', [])}
    matched = {m[2] for m in rep.get(club, {}).get('matched', [])}
    tgt = []
    for pos in ('GK', 'DF', 'MF', 'FW'):
        for num, nm in sq.get(club, {}).get(pos, []) or []:
            tgt.append((nm, int(num) if str(num).isdigit() else 0, pos))
    # missing = target names that are NOT already matched (via matched real names)
    matched_reals = {m[0] for m in rep.get(club, {}).get('matched', [])}
    missing = [(nm, num, pos) for nm, num, pos in tgt if nm not in matched_reals]
    extras = [g for g in roster if g not in matched]
    # same-club proposals
    pairs = []
    for nm, num, pos in missing:
        best = None
        for g in extras:
            sc = nsim(nm, g)
            pj, ppid, povr = roster[g]
            if num and pj == num:
                sc += 0.25  # jersey number evidence
            if abs(povr - 75) < 40 and sc > 0.55:
                if best is None or sc > best[1]:
                    best = (g, sc)
        if best:
            pairs.append({'real': nm, 'num': num, 'game': best[0],
                          'score': best[1], 'jersey': roster[best[0]][1], 'ovr': roster[best[0]][2]})
    # cross-club proposals (intra-PL transfer): this club's missing vs OTHER clubs' extras
    xfers = []
    for nm, num, pos in missing:
        best = None
        for oc, otid in PL.items():
            if oc == club:
                continue
            otroster = {p['name']: (p['pid'], p['jersey'], p['attrs'][1])
                        for p in db['teams'].get(str(otid), {}).get('roster', [])}
            om = {m[2] for m in rep.get(oc, {}).get('matched', [])}
            for g, (pid, gj, govr) in otroster.items():
                if g in om:
                    continue
                sc = nsim(nm, g)
                if num and gj == num:
                    sc += 0.2
                if best is None or sc > best[2]:
                    best = (oc, g, sc, gj, govr, pid)
        if best and best[2] >= 0.62:
            xfers.append({'real': nm, 'num': num, 'src_club': best[0], 'src_game': best[1],
                          'score': best[2], 'src_jersey': best[3], 'src_ovr': best[4], 'src_pid': best[5]})
    out[club] = {'same_club': pairs, 'cross_club': xfers,
                 'n_missing': len(missing), 'n_extras': len(extras)}
    print('%-16s missing=%2d extras=%2d | same-club pairs=%d cross-club=%d' % (
        club, len(missing), len(extras), len(pairs), len(xfers)))

json.dump(out, open(BASE + r'\proposals.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n== same-club proposals (review) ==')
for club, o in out.items():
    for p in o['same_club']:
        print('  %-16s %-24s <-> %-18s sc=%.2f (#%s ovr%s)' % (
            club, p['real'], p['game'], p['score'], p['jersey'], p['ovr']))
print('\n== cross-club proposals (review) ==')
for club, o in out.items():
    for p in o['cross_club']:
        print('  %-16s %-24s <- %s/%-16s sc=%.2f (#%s ovr%s)' % (
            club, p['real'], p['src_club'], p['src_game'], p['score'], p['src_jersey'], p['src_ovr']))
