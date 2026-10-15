# -*- coding: utf-8 -*-
"""build_alias.py - master game_name -> real_name alias for the 20 PL clubs.
ONLY the 189 verified matched pairs (pl_gap_report.json). No guessing:
player records are shared across clubs + national teams, so a wrong rename has
wide blast radius. Transfer targets are added dynamically in the engine (they are
individually verified there).
"""
import json

BASE = r'D:\FL26_Mod\work\fc26_alignment'
rep = json.load(open(BASE + r'\pl_gap_report.json', encoding='utf-8'))

alias = {}
for club, r in rep.items():
    for real, num, gname, gjersey, score in r['matched']:
        alias[gname] = real

json.dump(alias, open(BASE + r'\name_legalize.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('verified alias table: %d entries (189 matched pairs)' % len(alias))
