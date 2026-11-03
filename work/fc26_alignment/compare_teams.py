# -*- coding: utf-8 -*-
"""compare_teams.py - compare each target club's LATEST wiki squad (wiki_nov)
against the in-game roster (game_rosters.json). Fuzzy surname matching for
legalized game names. Output: nov_team_compare.json + console per-league summary.
"""
import json, os, re, sys, unicodedata, difflib

BASE = r'D:\FL26_Mod\work\fc26_alignment'
NEW = os.path.join(BASE, 'wiki_nov')


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def toks(s):
    s = strip_acc(s).lower()
    s = re.sub(r"[^a-z\s\-]", ' ', s)
    out = []
    for part in s.split():
        out.extend([p for p in re.split(r'-+', part) if p])
    return out


def parse_wiki_squad(path):
    txt = open(path, encoding='utf-8').read()
    # section-aware: keep only first-team current squad sections
    sec = '?'
    players = []
    for line in txt.splitlines():
        ls = line.strip()
        if ls.startswith('==') and ls.endswith('=='):
            sec = ls.strip('=').strip().lower()
            continue
        if not re.match(r'\{\{[Ff]s2? ?player|\{\{football squad player', ls):
            continue
        if not any(k in sec for k in ('current squad', 'first-team squad', 'first team squad', 'squad information')):
            continue
        m = re.match(r'\{\{([Ff]s2? ?player|football squad player)(.*)\}\}\s*$', ls)
        if not m:
            continue
        body = m.group(2)
        def f(k):
            mm = re.search(r'\|\s*%s\s*=\s*([^|}]*)' % k, body)
            return mm.group(1).strip() if mm else ''
        no, pos = f('no'), f('pos').upper()
        nm = f('name')
        mm = re.search(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', nm)
        if mm:
            nm = mm.group(1)
        nm = re.sub(r'\[\[|\]\]', '', nm).split('|')[0].strip()
        if nm and no.isdigit():
            players.append({'no': int(no), 'pos': pos, 'name': nm})
    seen = set()
    out = []
    for p in sorted(players, key=lambda x: x['no']):
        k = (p['no'], p['name'].lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def score(gname, wname):
    g = toks(gname)
    w = toks(wname)
    if not g or not w:
        return 0.0
    if g == w:
        return 3.0
    gs, ws = g[-1], w[-1]
    sr = difflib.SequenceMatcher(None, gs, ws).ratio()
    fi = (g[0][0] == w[0][0]) if (g and w) else False
    if gs == ws and fi:
        return 2.8
    if sr >= 0.85 and fi:
        return 2.5
    if gs == ws:
        return 2.2
    if sr >= 0.80:
        return 2.0
    common = set(g) & set(w)
    if common and max(len(t) for t in common) >= 4:
        return 1.5
    return 0.0


def main():
    targets = json.load(open(BASE + r'\nov_target_pages.json', encoding='utf-8'))
    rosters = json.load(open(BASE + r'\game_rosters.json', encoding='utf-8'))
    report = {}
    nmatch = nmiss = nextra = 0
    for title, v in sorted(targets.items()):
        p = os.path.join(NEW, title.replace('/', '_') + '.txt')
        if not os.path.exists(p):
            p2 = os.path.join(BASE, 'wiki', title + '.txt')
            if os.path.exists(p2):
                p = p2
            else:
                print('NO PAGE:', title)
                continue
        wiki = parse_wiki_squad(p)
        tid = str(v['tid'])
        g = rosters.get(tid)
        game = g['players'] if g else []
        # match
        matches = {}
        used = set()
        for wp in wiki:
            best, bs = None, 0.0
            for gi, gp in enumerate(game):
                if gi in used:
                    continue
                s = score(gp[1], wp['name'])
                if s > bs:
                    bs, best = s, gi
            if best is not None and bs >= 2.0:
                matches[wp['name']] = {'pid': game[best][0], 'gname': game[best][1],
                                       'ovr': game[best][2], 'jersey': game[best][3], 'score': bs}
                used.add(best)
            elif best is not None and bs >= 1.5:
                matches.setdefault('__weak__', []).append(
                    {'wiki': wp['name'], 'gname': game[best][1], 'pid': game[best][0], 'score': bs})
        weak_names = set()
        weak_pids = set()
        for w in matches.get('__weak__', []):
            weak_names.add(w['wiki'])
            weak_pids.add(w['pid'])
        missing = [wp for wp in wiki if wp['name'] not in matches and wp['name'] not in weak_names]
        extra = [gp for gi, gp in enumerate(game) if gi not in used and gp[0] not in weak_pids]
        nmatch += len(matches)
        nmiss += len(missing)
        nextra += len(extra)
        report[tid] = {'league': v['league'], 'club': v['club'], 'title': title,
                       'wiki_n': len(wiki), 'game_n': len(game),
                       'matched': matches, 'missing': missing, 'extra': extra}
    json.dump(report, open(BASE + r'\nov_team_compare.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('clubs: %d | matched %d | wiki-only(missing in game) %d | game-only %d'
          % (len(report), nmatch, nmiss, nextra))
    # per-league summary
    import collections
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for tid, v in report.items():
        a = agg[v['league']]
        a[0] += 1
        a[1] += len(v['missing'])
        a[2] += len(v['extra'])
        a[3] += v['wiki_n']
    print('%-10s %5s %6s %6s %7s' % ('league', 'clubs', 'missing', 'extra', 'wikiN'))
    for lg, a in sorted(agg.items()):
        print('%-10s %5d %6d %6d %7d' % (lg, a[0], a[1], a[2], a[3]))


if __name__ == '__main__':
    main()
