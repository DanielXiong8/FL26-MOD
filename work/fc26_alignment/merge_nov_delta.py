# -*- coding: utf-8 -*-
"""merge_nov_delta.py - fold nov_delta.json ops into pl_plan.json (idempotent-ish).

- INJECT appended at END (keeps existing injected pids stable for save compat)
- REMOVEs targeting injected pids (>=175923) become INJECT-list deletions instead
  (engine REMOVE runs before injects, so it cannot remove a fresh injection)
- duplicate inject names within the same team are dropped
"""
import json, os, shutil

BASE = r'D:\FL26_Mod\work\fc26_alignment'
INJ_PID_START = 175923

plan = json.load(open(BASE + r'\pl_plan.json', encoding='utf-8'))
delta = json.load(open(BASE + r'\nov_delta.json', encoding='utf-8'))

before = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
print('plan before:', before)

# --- REMOVEs: split into base-pid removes vs injected-pid inject-list deletions
removes_ok = []
inj_dropped = 0
for r in delta['removes']:
    if r['pid'] < INJ_PID_START:
        removes_ok.append(r)
        continue
    hit = None
    for e in plan['INJECT']:
        if e['team_id'] == r['team'] and e['name'] == r['name']:
            hit = e
            break
    if hit:
        plan['INJECT'].remove(hit)
        inj_dropped += 1
    else:
        print('  WARN injected-pid remove not matched:', r)
plan['REMOVE'] += removes_ok
print('removes: %d base-pid + %d inject-list drops' % (len(removes_ok), inj_dropped))

# --- RENAME: [pid, name] pairs; skip pid if already renamed to same name
existing_ren = dict(plan['RENAME'])
nr = 0
for r in delta['renames']:
    if existing_ren.get(str(r['pid'])) == r['name']:
        continue
    plan['RENAME'][str(r['pid'])] = r['name']
    nr += 1
print('renames added:', nr)

# --- TRANSFER append
plan['TRANSFER'] += delta['transfers']
print('transfers added:', len(delta['transfers']))

# --- INJECT append with dedupe by (team_id, name)
seen = {(e['team_id'], e['name']) for e in plan['INJECT']}
added = 0
for e in delta['injects']:
    k = (e['team_id'], e['name'])
    if k in seen:
        continue
    seen.add(k)
    plan['INJECT'].append(e)
    added += 1
print('injects added:', added, '(dup skipped: %d)' % (len(delta['injects']) - added))

after = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
print('plan after:', after)
json.dump(plan, open(BASE + r'\pl_plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('pl_plan.json saved')
