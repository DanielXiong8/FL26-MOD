# -*- coding: utf-8 -*-
"""
Diagnose post-injection issues reported by user (2026-09-01):
1) Original players' face models missing after injection
2) New player age shows 1800
3) New player preferred foot not shown
"""
import struct, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        if isinstance(raw, str):
            raw = raw.encode('utf-8', errors='surrogateescape')
        assets[d.m_Name] = bytes(raw)

print("TextAssets:", len(assets))

# ---------- Parse Players ----------
raw = assets['Players']
assert raw[:8] == b"plyrcsv0"
off = 8
ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
print(f"players: {pcnt}")
recs = []
for i in range(pcnt):
    pid = struct.unpack_from("<I", raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", raw, off)[0]; off += 2
    name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
    b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
    attrs = list(raw[off:off+17]); off += 17
    tail16 = struct.unpack_from("<H", raw, off)[0]; off += 2
    tail8 = raw[off]; off += 1
    year = struct.unpack_from("<I", raw, off)[0]; off += 4
    recs.append(dict(idx=i, pid=pid, name=name, fa=fa, fb=fb, fc=fc, nat=nat,
                     b1=b1, b16=b16, b0=b0, tail16=tail16, tail8=tail8, year=year))

# ---------- Field distributions ----------
print("\n=== Field value distributions (top 8) ===")
for f in ['fa','fb','fc','b1','b16','b0','tail16','tail8']:
    c = Counter(r[f] for r in recs)
    print(f"{f}: {c.most_common(8)}")

print("\n=== year distribution ===")
years = [r['year'] for r in recs]
print("min/max:", min(years), max(years))
c = Counter(y for y in years if 1970 <= y <= 2015)
print("count in 1970-2015:", sum(c.values()), "of", len(years))
c2 = Counter(y for y in years if not (1970 <= y <= 2015))
print("out-of-range values:", c2.most_common(10))
print("sample years:", sorted(c.items())[:5], "...", sorted(c.items())[-5:])

# ---------- Known Arsenal players' full records ----------
arsenal = [103346, 110947, 103281, 103643, 119091, 100389]
print("\n=== Sample real players (full raw fields) ===")
for r in recs:
    if r['pid'] in arsenal:
        print(f"pid={r['pid']} idx={r['idx']} name={r['name'][:20]!r} fa={r['fa']} fb={r['fb']} fc={r['fc']} nat={r['nat']} b1={r['b1']} b16={r['b16']} b0={r['b0']} tail16={r['tail16']} tail8={r['tail8']} year={r['year']}")

# foot guess: field with dominant 2-value distribution
print("\n=== Foot candidates: fields with 2 dominant values ===")
for f in ['fa','fb','fc','b1','b16','b0','tail16','tail8']:
    c = Counter(r[f] for r in recs)
    if 1 <= len(c) <= 6:
        print(f"{f}: {c.most_common()}")

# ---------- PlayerAppearanceTable ----------
print("\n=== PlayerAppearanceTable ===")
pa = assets.get('PlayerAppearanceTable')
if pa:
    print("size:", len(pa))
    print("head hex:", pa[:32].hex())
    n = struct.unpack_from("<I", pa, 0)[0]
    print("first uint32:", n)
    body = len(pa) - 8
    for div in [pcnt, 46515, 52640, n]:
        if div:
            print(f"  size/{div} = {body/div:.4f}")
    # does it contain pids?
    for pid in arsenal + [180001]:
        t = struct.pack("<I", pid)
        idx = pa.find(t)
        print(f"  pid {pid}: {'@0x%x' % idx if idx>=0 else 'not found'}")

# ---------- ClubPlayer alignment check ----------
print("\n=== ClubPlayer ===")
cp = assets.get('ClubPlayer')
if cp:
    n1 = struct.unpack_from("<I", cp, 0)[0]
    n2 = (len(cp) - 4 - n1*8) // 17
    print(f"sec1 teams={n1}, sec2 records={n2}, leftover={(len(cp)-4-n1*8) % 17}")
    # team 20030 block
    off = 4 + n1*8
    # find team 20030 in sec1 by order
    for i in range(n1):
        tid, cnt = struct.unpack_from("<II", cp, 4 + i*8)
        if tid == 20030:
            print(f"team 20030: sec1 idx={i} cnt={cnt}")
    # where does 20030 block start in sec2 (first occurrence)
    base = 4 + n1*8
    first = None
    pids20030 = []
    for j in range(n2):
        tid = struct.unpack_from("<I", cp, base + j*17)[0]
        if tid == 20030:
            if first is None: first = j
            pids20030.append(struct.unpack_from("<I", cp, base + j*17 + 4)[0])
    print(f"team 20030 sec2 first idx={first}, count={len(pids20030)}")
    print(f"pids: {pids20030}")
