# -*- coding: utf-8 -*-
"""setup_ea_probe.py — atomically (re)build the 6-variant EA probe roster."""
import sys
sys.path.insert(0, r'D:\FL26_Mod\tools\FL26_FaceBuilderWeb\backend')
import registry as reg
from appearance_state import POS_TEMPLATES

ATTRS = POS_TEMPLATES['FW']
PROBES = [
    (175924, 'EA_13', 30, 13),
    (175925, 'EA_14', 31, 14),
    (175926, 'EA_15', 32, 15),
    (175927, 'EA_16', 33, 16),
    (175928, 'EA_17', 34, 17),
    (175929, 'EA_18', 45, 18),
]
r = reg.load()
# keep players from OTHER teams; drop all 20030 test entries
r['players'] = [p for p in r['players'] if p.get('team_id') != 20030]
for pid, name, jersey, b14 in PROBES:
    r['players'].append({'pid': pid, 'name': name, 'team_id': 20030, 'jersey': jersey,
                         'apk_sha256': 'phase14b-ea-variant-probe', 'slot_note': 'EA variant probe',
                         'created': '2026-09-12', 'attrs': list(ATTRS), 'nat': 24,
                         'face_texture_id': 10, 'b14': b14})
reg.save(r)
final = [(p['pid'], p['name'], p['jersey'], p.get('b14')) for p in reg.by_team(20030)]
print('20030 roster:', final)
assert len(final) == 6, 'roster count'
assert sorted(x[3] for x in final) == [13, 14, 15, 16, 17, 18]
print('EA variant roster READY')
