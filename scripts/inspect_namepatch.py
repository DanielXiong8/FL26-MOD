# -*- coding: utf-8 -*-
"""Inspect PlayerNamePatch + find firstname table. Read-only."""
import io, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    names = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read(check_read=False)
        nm = getattr(d, "m_Name", "")
        names.append(nm)
        if nm in ("PlayerNamePatch", "firstname", "lastname2", "femalefirstname", "femalelastname"):
            raw = getattr(d, "m_Script", b"")
            if isinstance(raw, str):
                raw = raw.encode("utf-8", errors="surrogateescape")
            print(f"=== {nm} ({len(raw):,}B) ===")
            print("head hex:", raw[:48].hex(" "))
            print("preview:", raw[:600].decode("utf-8", errors="replace").encode("ascii", errors="replace").decode("ascii").replace("\x00", "|")[:500])
            print()
    fn = [n for n in names if "first" in n.lower() or "name" == n.lower()]
    print("name-table candidates:", fn)

if __name__ == "__main__":
    sys.exit(main())
