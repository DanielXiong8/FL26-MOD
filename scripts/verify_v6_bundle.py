# -*- coding: utf-8 -*-
"""
Verify v6 modified bundle:
1) New player 180001 record read-back (year, tail16, etc.)
2) ClubPlayer insert position correctness (sec1 sum vs actual block location)
3) Players table byte-exactness for original 52,640 records (corruption check)
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

def load_asset(bundle, name):
    env = UnityPy.load(bundle)
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read(check_read=False)
            if d.m_Name == name:
                raw = d.m_Script
                if isinstance(raw, str):
                    raw = raw.encode('utf-8', errors='surrogateescape')
                return bytes(raw)
    return None

def parse_players(raw):
    off = 8
    ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
    for _ in range(ncnt):
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
    pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
    recs = []
    for i in range(pcnt):
        start = off
        pid = struct.unpack_from("<I", raw, off)[0]; off += 4
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16 = struct.unpack_from("<H", raw, off)[0]; off += 2
        tail8 = raw[off]; off += 1
        year = struct.unpack_from("<I", raw, off)[0]; off += 4
        recs.append(dict(pid=pid, name=name, fa=fa, fb=fb, fc=fc, nat=nat,
                         b1=b1, b16=b16, b0=b0, tail16=tail16, tail8=tail8,
                         year=year, attrs=attrs, raw_bytes=raw[start:off]))
    return recs

orig_players = load_asset(r'C:\FL26_Mod\build\gamedata.unity3d', 'Players')
mod_players  = load_asset(r'C:\FL26_Mod\modified\gamedata_v6.unity3d', 'Players')
orig_cp = load_asset(r'C:\FL26_Mod\build\gamedata.unity3d', 'ClubPlayer')
mod_cp  = load_asset(r'C:\FL26_Mod\modified\gamedata_v6.unity3d', 'ClubPlayer')

ro = parse_players(orig_players)
rm = parse_players(mod_players)
print(f"Players orig={len(ro)} mod={len(rm)}")

# 1) new player record
np = [r for r in rm if r['pid'] == 180001]
if np:
    r = np[0]
    print(f"\n[1] New player read-back: pid={r['pid']} name={r['name']!r} fa={r['fa']} fb={r['fb']} fc={r['fc']} nat={r['nat']}")
    print(f"    b1={r['b1']} b16={r['b16']} b0={r['b0']} tail16={r['tail16']} tail8={r['tail8']} year={r['year']}")
    print(f"    attrs={r['attrs']}")
    print(f"    position in table: index {rm.index(r)} of {len(rm)}")
else:
    print("\n[1] 180001 NOT FOUND in modified bundle!")

# 2) original records byte-exact?
print("\n[2] Original-record integrity check:")
mismatch = 0
first_bad = None
om = {r['pid']: r for r in rm}
for r in ro:
    m = om.get(r['pid'])
    if m is None:
        mismatch += 1
        if first_bad is None: first_bad = ('missing', r['pid'])
        continue
    for k in ['name','fa','fb','fc','nat','b1','b16','b0','tail16','tail8','year','attrs']:
        if r[k] != m[k]:
            mismatch += 1
            if first_bad is None: first_bad = (r['pid'], k, r[k], m[k])
            break
print(f"    mismatched original records: {mismatch} / {len(ro)}")
if first_bad: print(f"    first bad: {first_bad}")

# also raw byte check: is the orig players table a byte-prefix of mod table (up to same content)?
# find byte offset of pid 180001 in mod raw
t = struct.pack("<I", 180001)
i = mod_players.find(t)
print(f"    pid 180001 raw offset in mod: 0x{i:x}, mod total={len(mod_players)}, orig total={len(orig_players)}")

# 3) ClubPlayer check
def parse_cp(raw):
    n1 = struct.unpack_from("<I", raw, 0)[0]
    sec1 = []
    for i in range(n1):
        tid, cnt = struct.unpack_from("<II", raw, 4 + i*8)
        sec1.append((tid, cnt))
    sec2 = []
    base = 4 + n1*8
    j = 0
    while base + j*17 + 17 <= len(raw):
        tid, pid, f1, f2 = struct.unpack_from("<IIII", raw, base + j*17)
        f3 = raw[base + j*17 + 16]
        sec2.append((tid, pid, f1, f2, f3))
        j += 1
    return sec1, sec2

s1o, s2o = parse_cp(orig_cp)
s1m, s2m = parse_cp(mod_cp)
print(f"\n[3] ClubPlayer: sec2 orig={len(s2o)} mod={len(s2m)}")

# where is 180001 in mod sec2?
pos = [i for i, r in enumerate(s2m) if r[1] == 180001]
print(f"    180001 sec2 positions in mod: {pos}")
for p in pos:
    lo = max(0, p-2); hi = min(len(s2m), p+3)
    for q in range(lo, hi):
        print(f"      [{q}] team={s2m[q][0]} pid={s2m[q][1]} f1={s2m[q][2]} f2={s2m[q][3]} f3={s2m[q][4]}")

# expected insert pos per v6 logic: sum of cnt for sec1 entries before team 20030 (in sec1 order)
tidx = [i for i, (t, c) in enumerate(s1o) if t == 20030][0]
expected = sum(c for i, (t, c) in enumerate(s1o) if i < tidx)
print(f"    team 20030 sec1 idx={tidx}, v6 insert_pos={expected}")
# actual first occurrence of 20030 in orig sec2
first20030 = next(i for i, r in enumerate(s2o) if r[0] == 20030)
print(f"    actual first 20030 record in orig sec2: idx={first20030}")
print(f"    MATCH: {expected == first20030}")

# sec1 count for 20030 in mod
print(f"    sec1 cnt 20030: orig={s1o[tidx][1]} mod={s1m[tidx][1]}")

# check every team's block contiguity in mod sec2
print("\n[4] Team block contiguity in MOD sec2 (scan-order vs sec1 order):")
last_team = None
transitions = 0
team_seen = {}
order = []
for i, r in enumerate(s2m):
    if r[0] != last_team:
        transitions += 1
        order.append((i, r[0]))
        last_team = r[0]
print(f"    transitions={transitions} (sec1 teams={len(s1m)})")
# find teams whose records are NOT contiguous
from collections import defaultdict
spans = defaultdict(list)
for i, r in enumerate(s2m):
    spans[r[0]].append(i)
broken = []
for t, idxs in spans.items():
    if idxs != list(range(idxs[0], idxs[0]+len(idxs))):
        broken.append((t, idxs[0], len(idxs)))
print(f"    non-contiguous teams: {len(broken)}")
for b in broken[:10]:
    print(f"      team {b[0]}: first_idx={b[1]} n={b[2]}")
