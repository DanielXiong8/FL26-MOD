# -*- coding: utf-8 -*-
"""fetch_dqd.py - fetch real six-stat abilities from dongqiudi player pages.
search API: api.dongqiudi.com/search?keywords=NAME -> players[].person_id
player page: dongqiudi.com/player/<person_id>.html -> server-rendered radar:
  综合能力 score + labels [速度,力量,防守,盘带,传球,射门] + vals
Output: dqd_abilities.json {clean_name: {'ovr':int,'pac':int,'sho':int,'pas':int,'dri':int,'def':int,'phy':int}}
Resumable: skips names already in output.
"""
import json, os, re, subprocess, time, urllib.parse

BASE = r'D:\FL26_Mod\work\fc26_alignment'
OUT = os.path.join(BASE, 'dqd_abilities.json')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'


def curl(url, binary=False):
    for attempt in range(3):
        r = subprocess.run(['curl', '-sS', '--compressed', '--max-time', '35',
                            url, '-H', 'User-Agent: ' + UA,
                            '-H', 'Referer: https://www.dongqiudi.com/'],
                           capture_output=True)
        if r.returncode == 0 and (r.stdout or binary):
            return r.stdout
        time.sleep(1.5)
    return b''


def search_player(name):
    u = 'https://api.dongqiudi.com/search?keywords=' + urllib.parse.quote(name) + '&page=1'
    raw = curl(u)
    try:
        data = json.loads(raw)
        pls = data.get('players') or []
        return pls[0].get('person_id') if pls else None
    except Exception:
        return None


LABEL = {'速度': 'pac', '射门': 'sho', '传球': 'pas', '盘带': 'dri', '防守': 'def', '力量': 'phy'}


def parse_page(html):
    m = (re.search(r'综合能力</div>\s*<div class="pp-ability__score"[^>]*>(\d+)</div>', html)
         or re.search(r'综合能力.{0,200}?pp-ability__score"[^>]*>(\d+)<', html, re.S))
    labels = re.findall(r'pp-ability__label"[^>]*>([^<]+)</span>', html)
    vals = re.findall(r'pp-ability__val"[^>]*>(\d+)<', html)
    if not m or len(vals) < 6:
        return None
    d = {'ovr': int(m.group(1))}
    for lab, v in zip(labels, vals):
        k = LABEL.get(lab.strip())
        if k:
            d[k] = int(v)
    return d if len(d) >= 5 else None


def main():
    plan = json.load(open(BASE + r'\pl_plan.json', encoding='utf-8'))
    names = sorted({e['name'] for e in plan['INJECT']})
    out = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    todo = [n for n in names if n not in out]
    print('todo %d / %d (cached %d)' % (len(todo), len(names), len(out)))
    ok = fail = 0
    for k, nm in enumerate(todo):
        pid = search_player(nm)
        if not pid:
            fail += 1
            continue
        html_b = curl('https://www.dongqiudi.com/player/%s.html' % pid)
        try:
            html = html_b.decode('utf-8', errors='replace')
        except Exception:
            html = ''
        ab = parse_page(html)
        if ab:
            out[nm] = ab
            ok += 1
        else:
            fail += 1
        if (k + 1) % 50 == 0:
            json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('  %d/%d ok=%d fail=%d' % (k + 1, len(todo), ok, fail))
        time.sleep(0.7)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE ok=%d fail=%d total=%d' % (ok, fail, len(out)))


if __name__ == '__main__':
    main()
