# -*- coding: utf-8 -*-
"""
replace_bundle.py — rebuild APK replacing exactly one entry; all other entries byte-identical.
Preserves per-entry compression (STORED/DEFLATE). Output: C:\FL26_Mod\build\base_mod.apk
"""
import os, sys, zipfile

SRC_APK = r"C:\FL26_Mod\working\base.apk"
DST_APK = r"C:\FL26_Mod\build\base_mod.apk"
MOD_DIR = r"C:\FL26_Mod\modified"

def main():
    entry = "assets/bundles/gamedata.unity3d"
    mod_path = os.path.join(MOD_DIR, entry.replace("/", "_"))
    with open(mod_path, "rb") as f:
        mod_bytes = f.read()

    os.makedirs(os.path.dirname(DST_APK), exist_ok=True)
    with zipfile.ZipFile(SRC_APK) as zin, \
         zipfile.ZipFile(DST_APK, "w") as zout:
        replaced = 0
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == entry:
                data = mod_bytes; replaced += 1
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.internal_attr = info.internal_attr
            ni.create_system = info.create_system
            ni.extra = info.extra
            ni.comment = info.comment
            zout.writestr(ni, data)
    assert replaced == 1, f"replaced={replaced}"
    print(f"rebuilt APK -> {DST_APK} ({os.path.getsize(DST_APK):,} bytes), replaced entry: {entry}")

if __name__ == "__main__":
    sys.exit(main())
