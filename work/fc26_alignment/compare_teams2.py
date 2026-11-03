# -*- coding: utf-8 -*-
"""compare_teams2.py - v2 matcher: jersey-number first pass, disambig-stripping,
CJK-aware surname hypotheses, section-aware wiki parsing, Saudi template pages.
Output: nov_team_compare2.json
"""
import json, os, re, sys, unicodedata, difflib, collections

BASE = r'D:\FL26_Mod\work\fc26_alignment'
NEW = os.path.join(BASE, 'wiki_nov')


def safename(t):
    return t.replace(':', '_') + '.txt'


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def clean_wiki_name(raw):
    nm = raw
    m = re.search(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', nm)
    if m:
        nm = m.group(1)
    nm = re.sub(r'\[\[|\]\]', '', nm).split('|')[0].strip()
    nm = re.sub(r'\s*\((?:footballer|soccer|association football)[^)]*\)\s*$', '', nm).strip()
    return nm


def toks(s):
    s = strip_acc(s).lower()
    s = re.sub(r"[^a-z\s\-]", ' ', s)
    out = []
    for part in s.split():
        out.extend([p for p in re.split(r'-+', part) if p])
    out = [t for t in out if t not in ('al', 'el', 'bin', 'ibn')]
    return out


def parse_current_squad_section(txt):
    """names from the Current squad section, template or plain-table format."""
    players = []
    sec = None
    for line in txt.splitlines():
        ls = line.strip()
        if ls.startswith('==') and ls.endswith('=='):
            sec = ls.strip('=').strip().lower()
            continue
        if sec is None:
            sec = ''
        incurr = any(k in sec for k in ('current squad', 'first-team squad', 'first team squad'))
        m = re.match(r'\{\{([Ff]s2? ?player|football squad player)(.*)\}\}\s*$', ls)
        if m and incurr:
            body = m.group(2)
            def f(k):
                mm = re.search(r'\|\s*%s\s*=\s*([^|}]*)' % k, body)
                return mm.group(1).strip() if mm else ''
            no, pos = f('no'), f('pos').upper()
            nm = clean_wiki_name(f('name'))
            if nm and no.isdigit():
                players.append({'no': int(no), 'pos': pos, 'name': nm})
            continue
        if incurr and sec == 'current squad':
            for mm in re.finditer(r'\[\[([A-Za-z][^\]|]+)(?:\|([^\]]+))?\]\]', ls):
                nm = (mm.group(2) or mm.group(1)).strip()
                if re.match(r'^[A-Z][a-zA-Z\.\- ]{3,30}$', nm) and not re.match(
                        r'^(Category|Template|List of|File)', nm):
                    players.append({'no': None, 'pos': '', 'name': nm})
    seen = set()
    out = []
    for p in players:
        k = (p['no'], p['name'].lower())
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def parse_template_squad(txt):
    players = []
    txt = re.sub(r'<!--.*?-->', '', txt, flags=re.S)          # drop commented-out players
    m2 = re.search(r'\{\{football squad start[^}]*\}\}(.*?)\{\{football squad end\}\}', txt, re.S)
    if m2:
        txt = m2.group(1)
    txt = re.sub(r'\{\{football squad manager[^}]*\}\}', '', txt)   # drop manager row
    for m in re.finditer(r'\|\s*name\s*=\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', txt):
        nm = (m.group(2) or m.group(1)).strip()
        nm = clean_wiki_name(nm)
        if nm:
            players.append({'no': None, 'pos': '', 'name': nm})
    seen = set()
    out = []
    for p in players:
        k = p['name'].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


def match_score(gname, wname):
    g = toks(gname)
    w = toks(wname)
    if not g or not w:
        return 0.0
    if g == w:
        return 3.0
    best = 0.0
    # surname hypotheses: last token (western) or first token (CJK pinyin order)
    for gi, wi in ((g[-1], w[-1]), (g[0], w[0])):
        sr = difflib.SequenceMatcher(None, gi, wi).ratio()
        other_g = [t for t in g if t != gi]
        other_w = [t for t in w if t != wi]
        given_ok = bool(set(other_g) & set(other_w))
        if gi == wi:
            best = max(best, 2.2 if not given_ok else 2.6)
        elif sr >= 0.85:
            best = max(best, 2.3 if given_ok else 2.0)
        elif sr >= 0.78:
            best = max(best, 1.9)
    common = set(g) & set(w)
    if len(common) >= 2:
        best = max(best, 2.2)
    elif common and max(len(t) for t in common) >= 5:
        best = max(best, 1.6)
    return best


def main():
    targets = json.load(open(BASE + r'\nov_target_pages.json', encoding='utf-8'))
    rosters = json.load(open(BASE + r'\game_rosters.json', encoding='utf-8'))
    report = {}
    for title, v in sorted(targets.items()):
        p = os.path.join(NEW, safename(title))
        if not os.path.exists(p):
            p2 = os.path.join(BASE, 'wiki', title + '.txt')
            if os.path.exists(p2):
                p = p2
            else:
                print('NO PAGE:', title)
                continue
        txt = open(p, encoding='utf-8').read()
        if v['league'] == 'SaudiT':
            wiki = parse_template_squad(txt)
        else:
            wiki = parse_current_squad_section(txt)
        tid = str(v['tid'])
        g = rosters.get(tid)
        game = g['players'] if g else []
        scores = {}
        for gi, gp in enumerate(game):
            for wp in wiki:
                s = match_score(gp[1], wp['name'])
                if s > 0:
                    scores[(gi, wp['name'])] = s
        pairs = sorted(scores.items(), key=lambda kv: -kv[1])
        matches = {}
        used = set()
        wused = set()
        for (gi, wn), s in pairs:
            if gi in used or wn in wused:
                continue
            if s < 1.5:
                continue
            matches[wn] = {'pid': game[gi][0], 'gname': game[gi][1], 'ovr': game[gi][2],
                           'jersey': game[gi][3], 'score': s}
            used.add(gi)
            wused.add(wn)
        # jersey-number pass for leftovers (wiki 'no' vs game jersey)
        for wp in wiki:
            if wp['name'] in wused or wp.get('no') is None:
                continue
            cands = [gi for gi, gp in enumerate(game)
                     if gi not in used and gp[3] == wp['no']]
            if len(cands) == 1:
                gi = cands[0]
                s = match_score(game[gi][1], wp['name'])
                if s >= 1.2 or toks(game[gi][1]) and toks(wp['name']):
                    matches[wp['name']] = {'pid': game[gi][0], 'gname': game[gi][1],
                                           'ovr': game[gi][2], 'jersey': game[gi][3],
                                           'score': 2.0 + s * 0.1, 'via': 'jersey'}
                    used.add(gi)
                    wused.add(wp['name'])
        missing = [wp for wp in wiki if wp['name'] not in wused]
        extra = [gp for gi, gp in enumerate(game) if gi not in used]
        report[tid] = {'league': v['league'], 'club': v['club'], 'title': title,
                       'wiki_n': len(wiki), 'game_n': len(game), 'matched_n': len(matches),
                       'matched': {k: vv for k, vv in matches.items() if k != '__w__'},
                       'missing': missing, 'extra': extra}
    json.dump(report, open(BASE + r'\nov_team_compare2.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    nmiss = sum(len(v['missing']) for v in report.values())
    nextra = sum(len(v['extra']) for v in report.values())
    print('clubs: %d | matched %d | missing %d | extra %d' % (
        len(report), sum(v['matched_n'] for v in report.values()), nmiss, nextra))
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for tid, v in report.items():
        a = agg[v['league']]
        a[0] += 1
        a[1] += len(v['missing'])
        a[2] += len(v['extra'])
        a[3] += v['wiki_n']
    print('%-10s %5s %7s %6s %6s' % ('league', 'clubs', 'wikiN', 'missing', 'extra'))
    for lg, a in sorted(agg.items()):
        print('%-10s %5d %7d %6d %6d' % (lg, a[0], a[3], a[1], a[2]))


if __name__ == '__main__':
    main()
