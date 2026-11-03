# -*- coding: utf-8 -*-
"""refresh_wiki.py - re-fetch ALL cached wiki pages fresh (Nov re-check) and diff.

For the 8-league full re-check: every cached page is re-fetched via the
Wikipedia API (5 titles/batch, local proxy), saved to wiki_nov/<title>.txt,
then compared against the October cache in wiki/<title>.txt.

Output: wiki_diff_report.json {title: {added: [lines], removed: [lines]}}
(only pages with any changed non-empty line; raw lines kept for analysis)
"""
import json, os, sys, difflib

BASE = r'D:\FL26_Mod\work\fc26_alignment'
sys.path.insert(0, BASE)
from wiki_bulk import api_get  # noqa

OLD = os.path.join(BASE, 'wiki')
NEW = os.path.join(BASE, 'wiki_nov')
os.makedirs(NEW, exist_ok=True)

titles = [f[:-4] for f in os.listdir(OLD) if f.endswith('.txt')]
titles = [t for t in titles if not os.path.exists(os.path.join(NEW, t.replace('/', '_') + '.txt'))]
print('cached pages: %d | todo (missing fresh copy): %d' % (len(titles) + sum(1 for f in os.listdir(NEW) if f.endswith('.txt')), len(titles)))

got, fail = {}, []
BATCH = 5
for i in range(0, len(titles), BATCH):
    batch = titles[i:i+BATCH]
    res = api_get(batch)
    if not res:
        fail.extend(batch)
        continue
    got.update(res)
    print('  %d/%d fetched' % (len(got), len(titles)), flush=True)
    for t, txt in res.items():
        with open(os.path.join(NEW, t.replace('/', '_') + '.txt'), 'w', encoding='utf-8') as f:
            f.write(txt)

print('fetched: %d | fail: %d' % (len(got), len(fail)))
if fail:
    print('failed titles:', fail[:10])

report = {}
changed = 0
for t in titles:
    p_old = os.path.join(OLD, t + '.txt')
    p_new = os.path.join(NEW, t.replace('/', '_') + '.txt')
    if not os.path.exists(p_new):
        continue
    old = open(p_old, encoding='utf-8').read().splitlines()
    new = open(p_new, encoding='utf-8').read().splitlines()
    added, removed = [], []
    for line in difflib.unified_diff(old, new, lineterm='', n=0):
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        s = line[1:].strip()
        if not s:
            continue
        (added if line.startswith('+') else removed).append(line[1:])
    if added or removed:
        changed += 1
        report[t] = {'added': added, 'removed': removed}

print('pages with changes: %d / %d' % (changed, len(titles)))
json.dump(report, open(os.path.join(BASE, 'wiki_diff_report.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('diff report saved')
