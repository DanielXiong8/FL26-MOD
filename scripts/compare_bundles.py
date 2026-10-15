# -*- coding: utf-8 -*-
"""Compare ALL TextAssets between original and v7 modified gamedata bundle (byte-level)."""
import sys, io, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

def dump_assets(path):
    env = UnityPy.load(path)
    out = {}
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read(check_read=False)
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', errors='surrogateescape')
            raw = bytes(raw)
            out[d.m_Name] = (len(raw), hashlib.md5(raw).hexdigest())
    return out

orig = dump_assets(r'C:\FL26_Mod\build\gamedata.unity3d')
mod  = dump_assets(r'C:\FL26_Mod\modified\gamedata_v7.unity3d')

print(f"orig assets: {len(orig)}, mod assets: {len(mod)}")
only_o = set(orig) - set(mod)
only_m = set(mod) - set(orig)
if only_o: print("missing in mod:", sorted(only_o)[:20])
if only_m: print("added in mod:", sorted(only_m)[:20])

diff = []
for name in sorted(set(orig) & set(mod)):
    so, ho = orig[name]
    sm, hm = mod[name]
    if ho != hm:
        diff.append((name, so, sm))
print(f"\ndiffering assets: {len(diff)}")
for name, so, sm in diff:
    print(f"  {name}: {so:,} -> {sm:,} bytes")
