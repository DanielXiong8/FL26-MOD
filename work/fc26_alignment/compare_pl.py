# -*- coding: utf-8 -*-
"""compare_pl.py - per-club side-by-side: current GAME roster (pid,game_name,jersey,ovr)
vs TARGET 2026-27 squad (real name, number, pos). Used to build the alias/transfer/
inject/remove tables for the 3-step aligner.
"""
import json

BASE = r'D:\FL26_Mod\work\fc26_alignment'
db = json.load(open(BASE + r'\db_survey.json', encoding='utf-8'))
sq = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))

# club display name -> team_id (from gap report tid)
out = {}
for club, r in rep.items():
    tid = r['tid']
    team = db['teams'].get(str(tid), {})
    game = [(p['pid'], p['name'], p['jersey'], p['attrs'][1]) for p in team.get('roster', [])]
    # target from squad file (pos -> [[num, name]])
    tgt = []
    for pos in ('GK', 'DF', 'MF', 'FW'):
        for num, nm in sq.get(club, {}).get(pos, []) or []:
            tgt.append([num, nm, pos])
    out[club] = {'tid': tid, 'display': team.get('display'), 'game': game, 'target': tgt}
    print('%-16s tid=%s game=%d target=%d' % (club, tid, len(game), len(tgt)))

json.dump(out, open(BASE + r'\pl_compare.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\nwrote pl_compare.json')
