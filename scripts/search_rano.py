# -*- coding: utf-8 -*-
"""Search ALL TextAssets in gamedata.unity3d for 'Rano' and other in-game League names. Read-only."""
import io, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"
PATTERNS = ["Rano", "rano", "RANO"]

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    hits = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read(check_read=False)
        nm = getattr(d, "m_Name", "")
        raw = getattr(d, "m_Script", b"")
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="surrogateescape")
        for pat in PATTERNS:
            p8 = pat.encode()
            p16 = pat.encode("utf-16-le")
            i8 = raw.find(p8)
            i16 = raw.find(p16)
            if i8 >= 0 or i16 >= 0:
                hits.append((nm, pat, i8, i16, len(raw)))
    print("Rano hits in gamedata TextAssets:")
    for h in hits:
        print("  ", h)
    if not hits:
        print("   NONE — 'Rano' does not exist anywhere in gamedata.unity3d")
    return 0

if __name__ == "__main__":
    sys.exit(main())
