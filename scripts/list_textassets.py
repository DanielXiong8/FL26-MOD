# -*- coding: utf-8 -*-
"""List all TextAsset names in gamedata.unity3d, grouped; find stat/card/rating candidates."""
import io, sys, zipfile
from collections import Counter
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    names = []
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read(check_read=False)
            names.append((getattr(d, "m_Name", ""), len(getattr(d, "m_Script", b""))))
    print(f"total TextAssets: {len(names)}")
    # group by prefix pattern
    pref = Counter()
    for n, s in names:
        key = n.split("_")[0] if "_" in n else n
        if key[:1].isdigit(): key = "(num)"
        pref[key] += 1
    print("\ntop prefixes:")
    for k, c in pref.most_common(40):
        print(f"  {k:30s} x{c}")
    # stat-like candidates
    print("\nstat/card/rating/ability candidates:")
    for n, s in sorted(names, key=lambda x: -x[1]):
        ln = n.lower()
        if any(k in ln for k in ("stat", "card", "rating", "ability", "skill", "attr", "radar", "power", "six", "overall", "quality", "talent", "potential")):
            print(f"  {n} ({s:,}B)")
    # biggest 40 textassets
    print("\nbiggest 40 TextAssets:")
    for n, s in sorted(names, key=lambda x: -x[1])[:40]:
        print(f"  {s:>10,}  {n}")

if __name__ == "__main__":
    sys.exit(main())
