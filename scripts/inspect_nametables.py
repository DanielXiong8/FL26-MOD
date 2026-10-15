# -*- coding: utf-8 -*-
"""Inspect lastname / PlayerNamePatch / firstname-like TextAssets in gamedata. Read-only."""
import io, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"
WANT = {"lastname", "firstname", "PlayerNamePatch", "name", "names"}

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read(check_read=False)
        nm = getattr(d, "m_Name", "")
        if nm not in WANT and "name" not in nm.lower():
            continue
        raw = getattr(d, "m_Script", b"")
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="surrogateescape")
        head = raw[:400]
        safe = head.decode("utf-8", errors="replace").encode("ascii", errors="replace").decode("ascii")
        print(f"=== {nm} ({len(raw):,}B) ===")
        print("head hex:", head[:32].hex(" "))
        print("text preview:", safe[:300].replace("\n", "\\n").replace("\x00", "|"))
        print()

if __name__ == "__main__":
    sys.exit(main())
