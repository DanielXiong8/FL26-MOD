# -*- coding: utf-8 -*-
"""Examine numeric-named TextAssets — are they per-player files keyed by player_id?"""
import io, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    num_names = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read(check_read=False)
        nm = getattr(d, "m_Name", "")
        if nm[:1].isdigit():
            num_names[nm] = (o, getattr(d, "m_Script", b""))
    print(f"numeric-named TextAssets: {len(num_names)}")
    keys = sorted(num_names.keys())
    print("first 20:", keys[:20])
    print("last 10:", keys[-10:])
    # is 100373 (Reno) / 116924 (Jerez) present?
    for probe in ("100373", "116924", "1039"):
        print(f"  {probe!r} exists: {probe in num_names}")
    # sample content of one
    sample_key = "100373" if "100373" in num_names else keys[0]
    o, raw = num_names[sample_key]
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="surrogateescape")
    print(f"\n=== sample {sample_key} ({len(raw):,}B) ===")
    print("head hex:", raw[:64].hex(" "))
    print("preview:", raw[:300].decode("utf-8", errors="replace").encode("ascii", errors="replace").decode("ascii").replace("\x00", "|"))

if __name__ == "__main__":
    sys.exit(main())
