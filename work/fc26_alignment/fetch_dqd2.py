# -*- coding: utf-8 -*-
"""fetch_dqd2.py - per-player: search full name -> pick candidate by token overlap
-> verify birth date (from our own inject_years when available) -> fetch player
page -> parse 综合能力+六维 -> store.
Resumable. Output: dqd_abilities.json
"""
import json, os, re, sys, time, unicodedata, urllib.parse

BASE = r'D:\FL26_Mod\work\fc26_alignment'
sys.path.insert(0, BASE)
from fetch_dqd import curl, parse_page, search_player  # noqa
OUT = os.path.join(BASE, 'dqd_abilities.json')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def search_all(name):
    u = 'https://api.dongqiudi.com/search?keywords=' + urllib.parse.quote(name) + '&page=1'
    raw = curl(u)
    try:
        return json.loads(raw).get('players') or []
    except Exception:
        return []


def toks(s):
    s = strip_acc(re.sub(r'<[^>]+>', '', s)).lower()
    return set(t for t in re.split(r'[^a-z]+', s) if len(t) >= 3)


def find_candidate(nm, birth_full):
    bt = birth_full[-4:] if birth_full else None
    for q in (nm, ' '.join(nm.split()[-2:]), nm.split()[-1]):
        pls = search_all(q)
        nt = toks(nm)
        cands = []
        for p in pls[:10]:
            en = strip_acc(re.sub(r'<[^>]+>', '', p.get('person_en_name') or '')).lower()
            pt = toks(en + ' ' + (p.get('person_name') or ''))
            ov = len(nt & pt)
            if ov >= 1:
                cands.append((ov, p))
        cands.sort(key=lambda x: -x[0])
        for ov, p in cands:
            dob = p.get('date_of_birth') or ''
            if bt and dob[-4:] == bt:
                return p, 'birth'
        if cands and not bt:
            return cands[0][1], 'token-only'
        if cands and bt:
            # birth mismatch but strong name: take best token match anyway (flagged)
            if cands[0][0] >= 2:
                return cands[0][1], 'name-only'
    return None, 'none'


def main():
    plan = json.load(open(BASE + r'\pl_plan.json', encoding='utf-8'))
    years = json.load(open(BASE + r'\inject_years.json', encoding='utf-8')) \
        if os.path.exists(BASE + r'\inject_years.json') else {}
    out = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    names = sorted({e['name'] for e in plan['INJECT']})
    todo = [n for n in names if n not in out]
    print('todo %d / %d' % (len(todo), len(names)))
    ok = hit = 0
    for k, nm in enumerate(todo):
        birth = None
        for e in plan['INJECT']:
            if e['name'] == nm:
                y = e.get('birth') or years.get(nm)
                if y:
                    birth = '%04d-01-01' % int(y)
                break
        cand, how = find_candidate(nm, birth)
        if cand:
            pid = cand.get('person_id')
            dob = cand.get('date_of_birth') or ''
            html = curl('https://www.dongqiudi.com/player/%s.html' % pid).decode('utf-8', errors='replace')
            ab = parse_page(html) or {}
            if ab:
                ab['dob'] = dob
                ab['match'] = how
                out[nm] = ab
                hit += 1
        ok += 1
        if (k + 1) % 40 == 0:
            json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('  %d/%d hit=%d' % (k + 1, len(todo), hit))
        time.sleep(0.5)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE hit=%d / %d (total stored %d)' % (hit, len(todo), len(out)))


if __name__ == '__main__':
    main()
