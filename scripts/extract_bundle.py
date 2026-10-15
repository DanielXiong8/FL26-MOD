# -*- coding: utf-8 -*-
"""extract_bundle.py — pull one bundle entry from working APK to extracted/. Read-only on APK."""
import sys, zipfile, hashlib, os

APK = r"C:\FL26_Mod\working\base.apk"
OUTDIR = r"C:\FL26_Mod\extracted"

def extract(entry: str) -> str:
    os.makedirs(OUTDIR, exist_ok=True)
    name = entry.replace("/", "_")
    out = os.path.join(OUTDIR, name)
    with zipfile.ZipFile(APK) as zf:
        data = zf.read(entry)
    with open(out, "wb") as f:
        f.write(data)
    sha = hashlib.sha256(data).hexdigest()
    print(f"extracted: {entry} -> {out}")
    print(f"size={len(data):,} sha256={sha}")
    return out

if __name__ == "__main__":
    extract(sys.argv[1] if len(sys.argv) > 1 else "assets/bundles/gamedata.unity3d")
