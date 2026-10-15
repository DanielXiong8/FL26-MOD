# -*- coding: utf-8 -*-
"""fetch_births.py - get real birth years for all INJECT players.
1) re-parse cached wiki club pages keeping RAW link titles (disambiguation kept)
2) map clean name -> raw title; fetch titles via API (5/call)
3) extract birth year from wikitext (birth date and age / birth year and age)
Output: inject_years.json {clean_name: year}
"""
import json, os, re, subprocess, sys, urllib.parse

BASE = r'D:\FL26_Mod\work\fc26_alignment'
WDIR = os.path.join(BASE, 'wiki')
sys.path.insert(0, BASE)
from wiki_bulk import api_get, clean_name

LEAGUE_PAGES = json.load(open(BASE + r'\league_pages.json', encoding='utf-8'))
try:
    M6 = json.load(open(BASE + r'\league_map6.json', encoding='utf-8'))
    for _lg, _cl in M6.items():
        for _k, (_pg, _t) in _cl.items():
            LEAGUE_PAGES.setdefault(_lg, {})[_k] = (_pg, _t)
except FileNotFoundError:
    pass

# 1) raw titles per clean name
raw_map = {}
for lg, clubs in LEAGUE_PAGES.items():
    for key, (page, tid) in clubs.items():
        if tid is None or not os.path.exists(os.path.join(WDIR, page + '.txt')):
            continue
        txt = open(os.path.join(WDIR, page + '.txt'), encoding='utf-8').read()
        for m in re.finditer(r'\{\{[Ff]s2? ?player([^{}]*)\}\}', txt):
            body = m.group(1)
            mm = re.search(r'\|\s*name\s*=\s*([^|}]*)', body)
            if not mm:
                continue
            raw = mm.group(1).strip()
            cm = re.search(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', raw)
            disp = cm.group(1) if cm else re.sub(r'\[\[|\]\]', '', raw).split('|')[0]
            disp = re.sub(r'\{\{[^{}]*\}\}', '', disp).strip()
            # raw title = the LINK TARGET (before |)
            tm = re.match(r'\[\[([^\]|]+)', raw)
            title = tm.group(1) if tm else None
            if title and disp:
                raw_map.setdefault(disp, title)

plan = json.load(open(BASE + r'\pl_plan.json', encoding='utf-8'))
names = sorted({e['name'] for e in plan['INJECT']})
titles = {}
missing = []
for nm in names:
    t = raw_map.get(nm)
    if t:
        titles[nm] = t
    else:
        missing.append(nm)
print('names:', len(names), '| raw title found:', len(titles), '| missing:', len(missing))

# 2) fetch and extract birth years
uniq_titles = sorted(set(titles.values()))
import time
got = {}
for attempt in range(3):
    got.update(api_get(uniq_titles))
    miss_t = [t for t in uniq_titles if t not in got]
    if not miss_t:
        break
    print('retry %d for %d titles' % (attempt + 1, len(miss_t)))
    uniq_titles = miss_t
    time.sleep(1.5)
got = api_get.__globals__['api_get'](sorted(set(titles.values())) ) if False else got

def birth_year(txt):
    for pat in (r'birth date and age\s*\|[^}]*?\|(\d{4})\|',
                r'birth date and age\|(\d{4})',
                r'birth year and age\|(\d{4})',
                r'Birth date and age[^\d]{0,40}(\d{4})',
                r'\|\s*birth_date\s*=\s*\{\{[Bb]irth date and age\|(\d{4})'):
        m = re.search(pat, txt)
        if m:
            y = int(m.group(1))
            if 1970 <= y <= 2009:
                return y
    return None

years, fail = {}, []
for nm, title in titles.items():
    key = title
    if key not in got:
        # redirect may land under another title
        cand = [k for k in got if k.lower().replace(' ', '_') == title.lower().replace(' ', '_')]
        key = cand[0] if cand else None
    if not key:
        fail.append(nm); continue
    y = birth_year(got[key])
    if y:
        years[nm] = y
    else:
        fail.append(nm)

# fallback: per-name search via generator (one call each)
import urllib.parse as _up
need = [n for n in names if n not in years]
print('search fallback for %d names' % len(need))
for k, nm in enumerate(need):
    q = _up.quote(nm)
    url = ('https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search'
           '&gsrsearch=' + q + '&gsrlimit=1&prop=revisions&rvprop=content&rvslots=main')
    for attempt in range(2):
        r = subprocess.run(['curl', '-sS', '--compressed', '--max-time', '40',
                            '-x', 'http://127.0.0.1:10808', url], capture_output=True, text=True)
        try:
            data = json.loads(r.stdout)
            pages = data.get('query', {}).get('pages', {})
            for p in pages.values():
                try:
                    y = birth_year(p['revisions'][0]['slots']['main']['*'])
                except Exception:
                    y = None
                if y:
                    years[nm] = y
            break
        except Exception:
            time.sleep(1.0)
    if (k + 1) % 60 == 0:
        print('  %d/%d' % (k + 1, len(need)))

print('birth years resolved: %d | unresolved: %d' % (len(years), len(fail)))
json.dump(years, open(BASE + r'\inject_years.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('sample:', dict(list(years.items())[:8]))
print('unresolved sample:', fail[:12])
