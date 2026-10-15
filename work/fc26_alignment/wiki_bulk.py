# -*- coding: utf-8 -*-
"""wiki_bulk.py - bulk Wikipedia wikitext fetch via API (local proxy) + squad parser.
Squad tables on enwiki use {{Fs player|no=|pos=|name=[[...]]}} templates.
Usage:
  python wiki_bulk.py fetch <titles_file>   # one title per line -> work/wiki/<title>.txt
  python wiki_bulk.py parse <title>         # print parsed squad for a cached page
"""
import json, os, re, subprocess, sys, urllib.parse

BASE = r'D:\FL26_Mod\work\fc26_alignment'
WDIR = os.path.join(BASE, 'wiki')
os.makedirs(WDIR, exist_ok=True)
PROXY = 'http://127.0.0.1:10808'


def api_get(titles):
    out = {}
    for i in range(0, len(titles), 5):
        batch = titles[i:i+5]
        t = urllib.parse.quote('|'.join(batch), safe='|')
        url = ('https://en.wikipedia.org/w/api.php?action=query&format=json&prop=revisions'
               '&rvprop=content&rvslots=main&redirects=1&titles=' + t)
        r = subprocess.run(['curl', '-sS', '--compressed', '--max-time', '60',
                            '-x', PROXY, url], capture_output=True, text=True)
        if r.returncode != 0:
            print('  FETCH FAIL batch %d: %s' % (i, r.stderr[:120]))
            continue
        try:
            data = json.loads(r.stdout)
        except Exception as e:
            print('  JSON FAIL batch %d: %s' % (i, e))
            continue
        # redirects mapping
        redir = {}
        for rd in data.get('query', {}).get('redirects', []):
            redir[rd['from']] = rd['to']
        for p in data.get('query', {}).get('pages', {}).values():
            title = p.get('title')
            try:
                txt = p['revisions'][0]['slots']['main']['*']
            except Exception:
                txt = ''
            out[title] = txt
    return out


def fetch(titles):
    titles = [t.replace('2026-27', '2026–27') for t in titles]
    todo = [t for t in titles if not os.path.exists(os.path.join(WDIR, t + '.txt'))]
    print('fetch %d/%d (cached %d)' % (len(todo), len(titles), len(titles) - len(todo)))
    got = api_get(todo)
    for title, txt in got.items():
        # save under requested alias if redirected
        alias = [t for t in todo if t == title or (title and t and
                 title.lower().replace(' ', '_') == t.lower().replace(' ', '_'))]
        fname = alias[0] if alias else title
        with open(os.path.join(WDIR, fname + '.txt'), 'w', encoding='utf-8') as f:
            f.write(txt)
    missing = [t for t in todo if not os.path.exists(os.path.join(WDIR, t + '.txt'))]
    if missing:
        print('  still missing:', missing)


def clean_name(raw):
    s = raw
    s = re.sub(r'\{\{[^{}]*\}\}', '', s)          # templates inside
    m = re.search(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', s)
    if m:
        s = m.group(1)
    s = re.sub(r'\[\[|\]\]', '', s)
    s = s.split('|')[0].strip()
    return s


def parse_squad(title):
    path = os.path.join(WDIR, title + '.txt')
    if not os.path.exists(path):
        path = os.path.join(WDIR, title.replace(' ', '_') + '.txt')
    txt = open(path, encoding='utf-8').read()
    players = {}
    for m in re.finditer(r'\{\{[Ff]s2? ?player([^{}]*)\}\}|\{\{football squad player([^{}]*)\}\}', txt):
        body = m.group(1) or m.group(2)
        def f(k):
            mm = re.search(r'\|\s*%s\s*=\s*([^|}]*)' % k, body)
            return mm.group(1).strip() if mm else ''
        no, pos, name = f('no'), f('pos'), clean_name(f('name'))
        nat = f('nat') or f('nationality') or ''
        if name and no.isdigit():
            players.setdefault((int(no), name), (pos, nat))
    # generic table fallback: |1||[[Name]] with POS in row (season pages)
    return [(no, name, pos, nat) for (no, name), (pos, nat) in sorted(players.items())]


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fetch':
        titles = [l.strip() for l in open(sys.argv[2], encoding='utf-8') if l.strip()]
        fetch(titles)
    elif cmd == 'parse':
        for row in parse_squad(sys.argv[2]):
            print('%s|%s|%s|%s' % row)
