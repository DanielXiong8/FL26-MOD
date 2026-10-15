# Phase 13B - Analysis 2: gamedata appearance byte statistics
# Full dump of Players + PlayerAppearanceTable, joined, with distributions.
import io, json, os, struct
from collections import Counter, defaultdict
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
GAMEDATA = os.path.join(ROOT, r'build\e2e_gamedata_src.unity3d')   # pristine pre-injection copy
OUT = os.path.join(ROOT, r'work\face_pipeline\phase13b\analysis')

env = UnityPy.load(GAMEDATA)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        nm = getattr(d, 'm_Name', '')
        if nm in ('Players', 'PlayerAppearanceTable', 'ClubPlayer'):
            assets[nm] = d.m_Script.encode('utf-8', errors='surrogateescape')
print('assets found:', list(assets))

# ---------- Players (plyrcsv0) ----------
def parse_plyrcsv0(raw):
    off = 8
    ncnt, = struct.unpack_from('<H', raw, off); off += 2
    nations = []
    for _ in range(ncnt):
        ln, = struct.unpack_from('<H', raw, off); off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    pcnt, = struct.unpack_from('<I', raw, off); off += 4
    recs = []
    for _ in range(pcnt):
        pid, = struct.unpack_from('<I', raw, off); off += 4
        ln, = struct.unpack_from('<H', raw, off); off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from('<HHHH', raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16, = struct.unpack_from('<H', raw, off); off += 2
        tail8 = raw[off]; off += 1
        year, = struct.unpack_from('<I', raw, off); off += 4
        recs.append(dict(pid=pid, name=name, fa=fa, fb=fb, fc=fc, nat=nat,
                         b1=b1, b16=b16, b0=b0, attrs=attrs, tail16=tail16, tail8=tail8, year=year))
    return nations, recs

nations, recs = parse_plyrcsv0(assets['Players'])
print('players:', len(recs), 'nations:', len(nations))

# ---------- PlayerAppearanceTable ----------
pa = assets['PlayerAppearanceTable']
n, = struct.unpack_from('<I', pa, 0)
idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
data_start = 4 + n*8
pa_map = {}
for pid, off in idx:
    rec = pa[off:off+21]
    app = list(rec[4:])   # 17 bytes
    pa_map[pid] = app
print('PA records:', len(pa_map))

# ---------- join + distributions ----------
both = [r for r in recs if r['pid'] in pa_map]
print('players WITH PA record:', len(both), '/', len(recs))
only_players = [r for r in recs if r['pid'] not in pa_map]
print('players WITHOUT PA record:', len(only_players), '(sample:', [r['name'] for r in only_players[:5]], ')')

def dist(key):
    c = Counter(r[key] for r in both)
    return dict(sorted(c.items()))

stats = {
    'players_b1': dist('b1'), 'players_b16': dist('b16'), 'players_b0': dist('b0'),
    'players_fa': {str(k): v for k, v in sorted(Counter(r['fa'] for r in both).items()) if v >= 5},
    'players_fb': {str(k): v for k, v in sorted(Counter(r['fb'] for r in both).items()) if v >= 5},
    'players_fc': {str(k): v for k, v in sorted(Counter(r['fc'] for r in both).items()) if v >= 5},
}
# PA bytes: app[0..16]; named b0..b16 (b1=face tex, b4=hair, b7=beard, b10=?, b14=shape)
for i in range(17):
    stats['pa_b%d' % i] = dist2 = dict(sorted(Counter(r['pid'] and pa_map[r['pid']][i] for r in both).items()))
# keep histograms small in stdout: show only top
for i in range(17):
    d = stats['pa_b%d' % i]
    top = sorted(d.items(), key=lambda kv: -kv[1])[:8]
    print('pa_b%-2d distinct=%-4d top: %s' % (i, len(d), top))

# ---------- cross-tabs of interest ----------
def cross(k1, k2, limit=15):
    ct = defaultdict(Counter)
    for r in both:
        ct[r[k1]][pa_map[r['pid']][k2]] += 1
    return {str(k): dict(v) for k, v in list(ct.items())[:limit]}

print()
print('fa x pa_b14:', cross('fa', 14))
print()
print('fa x pa_b1:', {k: v for k, v in list(cross('fa', 1).items())[:10]})

# full dump CSV for offline study
import csv
with open(os.path.join(OUT, 'players_pa_full.csv'), 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['pid','name','fa','fb','fc','nat','p_b1','p_b16','p_b0'] +
               ['pa_b%d'%i for i in range(17)] + ['tail16','tail8','year'])
    for r in both:
        w.writerow([r['pid'], r['name'], r['fa'], r['fb'], r['fc'], r['nat'], r['b1'], r['b16'], r['b0']] +
                   pa_map[r['pid']] + [r['tail16'], r['tail8'], r['year']])
print('CSV -> players_pa_full.csv')

json.dump(stats, open(os.path.join(OUT, 'appearance_stats.json'), 'w'), indent=1)
print('DONE')
