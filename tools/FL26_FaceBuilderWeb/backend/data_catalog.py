# -*- coding: utf-8 -*-
"""data_catalog.py — single source of truth for Teams / Nations / Reference Players /
appearance option tables. Reads REAL FL26 gamedata; no hardcoded game data here."""
import csv, io, json, os, struct
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
SRC_GAMEDATA = os.path.join(ROOT, 'build', 'e2e_gamedata_src.unity3d')
REF_JSON = os.path.join(ROOT, 'work', 'face_pipeline', 'phase13b', 'analysis', 'reference_players_chn.json')
CACHE = os.path.join(os.path.dirname(__file__), 'catalog_cache.json')

# device/device-chain verified appearance option tables (Phase 13B)
HAIR_COLORS = [  # b5 -> hairColorConfig mainColor (device: P04/P05/P06 pink/silver/brown)
    {'id': 0, 'hex': '6D3F02', 'name': '深棕 Dark Brown'},
    {'id': 1, 'hex': '816400', 'name': '棕黄 Olive Brown'},
    {'id': 2, 'hex': '403930', 'name': '黑炭 Near Black'},
    {'id': 3, 'hex': 'BCB274', 'name': '浅金沙 Sand Blonde'},
    {'id': 4, 'hex': '967E5F', 'name': '褐灰 Ash Brown'},
    {'id': 5, 'hex': 'B0787B', 'name': '粉红 Pink (device-confirmed)'},
    {'id': 6, 'hex': 'B0C4DE', 'name': '银蓝 Light Steel (device-confirmed)'},
    {'id': 7, 'hex': '403930', 'name': '黑炭 II'},
    {'id': 8, 'hex': 'C5B592', 'name': '米金 Wheat Blonde'},
    {'id': 9, 'hex': '403930', 'name': '黑炭 III'},
]
BEARDS = [{'id': i, 'name': 'Beard %d' % i} for i in range(1, 23)]          # b6, 22 styles (atlas)
EYEBROWS = [{'id': i, 'name': 'Eyebrow %d' % i} for i in range(1, 8)]       # b8, DB-verified subset
POSITIONS = [{'id': 'GK', 'note': 'attr template required'}, {'id': 'DF'}, {'id': 'MF'}, {'id': 'FW'}]


def _load_textasset(name):
    env = UnityPy.load(SRC_GAMEDATA)
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read(check_read=False)
            if d.m_Name == name:
                raw = d.m_Script
                return raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
    return None


def _load_strings_zh():
    """Localization table: key -> (EN, ZH_CN)."""
    raw = _load_textasset('strings')
    txt = raw.decode('utf-8', errors='replace')
    out = {}
    rdr = csv.reader(txt.split('\r\n'))
    hdr = next(rdr)
    try:
        i_en = hdr.index('EN')
        i_zh = hdr.index('ZH_CN')
    except ValueError:
        return out
    for r in rdr:
        if len(r) > max(i_en, i_zh) and r[0]:
            out[r[0]] = (r[i_en], r[i_zh])
    return out


def _parse_teams(loc):
    raw = _load_textasset('Teams')
    txt = raw.decode('utf-8', errors='replace')
    teams = {}
    for row in csv.reader(txt.split('\r\n')):
        if not row or not row[0].strip().isdigit():
            continue
        tid = int(row[0])
        nk = row[1] if len(row) > 1 else ''
        # 排除系统队（System/AllStar/SpecialPlayer/Duplicates/International 等）
        if nk in ('System', 'AllStar', 'SpecialPlayer', 'Duplicates', 'International'):
            continue
        is_nat = nk.startswith('Str_National')
        def L(key):
            v = loc.get(key)
            return (v[1] or v[0]) if v else key
        if is_nat:
            league = 'National Teams'
            display = L(nk) if nk in loc else (row[2] if len(row) > 2 and row[2] else nk.replace('Str_National_', '').replace('_', ' '))
        else:
            comp = row[6] if len(row) > 6 else ''
            league = L(comp) if comp and comp in loc else comp.replace('CompName_', '') if comp else 'Other'
            full = row[7].replace('Real_', '') if len(row) > 7 and row[7] else ''
            display = L(full) if full in loc else full.replace('_', ' ')
        teams[tid] = {
            'id': tid, 'name_key': nk, 'short': (row[3] if len(row) > 3 else ''),
            'display': display, 'league': league,
        }
    return teams


def _parse_nations():
    raw = _load_textasset('Players')
    off = 8
    ncnt, = struct.unpack_from('<H', raw, off); off += 2
    nations = []
    for _ in range(ncnt):
        ln, = struct.unpack_from('<H', raw, off); off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    return [{'code': i, 'name': n} for i, n in enumerate(nations)]


def _parse_roster_counts():
    """sec1 roster counts from baseline ClubPlayer (fresh-install state)."""
    raw = _load_textasset('ClubPlayer')
    n1, = struct.unpack_from('<I', raw, 0)
    out = {}
    for i in range(n1):
        tid, cnt = struct.unpack_from('<II', raw, 4 + i*8)
        out[tid] = cnt
    return out


def build_cache():
    loc = _load_strings_zh()
    teams = _parse_teams(loc)
    nations = _parse_nations()
    counts = _parse_roster_counts()
    refs = []
    if os.path.exists(REF_JSON):
        refs = json.load(open(REF_JSON, encoding='utf-8'))
    VERIFIED = {10059: 'China NT', 20026: 'Manchester City', 20030: 'Arsenal (London Red)'}
    team_list = []
    for tid, t in sorted(teams.items()):
        entry = dict(t)
        entry['roster_count'] = counts.get(tid, 0)
        entry['verified'] = tid in VERIFIED
        if tid in VERIFIED:
            entry['display'] = VERIFIED[tid]
        # V1: only real-club/national teams (id >= 10000), exclude system teams
        if tid >= 10000:
            # league already localized in _parse_teams (col6 CompName / National Teams);
            # women's national teams (_W suffix) get their own group
            nk = entry.get('name_key', '')
            if nk.startswith('Str_National') and nk.endswith('_W'):
                entry['league'] = '国家队（女子）Women National'
            team_list.append(entry)
    cache = {'teams': team_list, 'nations': nations, 'references': refs,
             'hair_colors': HAIR_COLORS, 'beards': BEARDS, 'eyebrows': EYEBROWS,
             'positions': POSITIONS,
             'roster_cap': 33, 'jersey_max': 99,
             'pa_defaults': {'b0': 6, 'b1': 14, 'b3': 16, 'b4': 0, 'b5': 2,
                             'b6': 1, 'b7': 0, 'b8': 1, 'b14': 17}}
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return cache


def get_cache(force=False):
    if force or not os.path.exists(CACHE):
        return build_cache()
    return json.load(open(CACHE, encoding='utf-8'))


if __name__ == '__main__':
    c = build_cache()
    print('teams with rosters:', len(c['teams']), '| nations:', len(c['nations']),
          '| references:', len(c['references']))
    print('sample team:', c['teams'][0])
