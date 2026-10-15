# -*- coding: utf-8 -*-
"""
arsc_pkg_rename.py — patch resources.arsc ResTable_package name field (fixed char16[128]).
In-place byte patch, size unchanged. Rebuilds APK with patched resources.arsc.
Input: build\base_renamed.apk (manifest already .mod) -> build\base_renamed2.apk
"""
import os, struct, sys, zipfile

SRC = r"C:\FL26_Mod\build\base_renamed.apk"
DST = r"C:\FL26_Mod\build\base_renamed2.apk"
OLD = "com.football.soccer.league"
NEW = "com.football.soccer.league.mod"

def main():
    with zipfile.ZipFile(SRC) as zf:
        arsc = bytearray(zf.read("resources.arsc"))
    # ResTable header: type=0x0002 hsize=12
    ttype, thsize, tsize = struct.unpack_from("<HHI", arsc, 0)
    assert ttype == 0x0002, f"not a ResTable: 0x{ttype:04x}"
    pkg_count = struct.unpack_from("<I", arsc, 8)[0]
    print(f"ResTable: {len(arsc):,}B packages={pkg_count}")

    patched = 0
    off = thsize
    while off < len(arsc):
        ctype, hsize, csize = struct.unpack_from("<HHI", arsc, off)
        if ctype == 0x0200:  # RES_TABLE_PACKAGE_TYPE
            pid = struct.unpack_from("<I", arsc, off + 8)[0]
            # name: char16[128] at off+12
            name_bytes = bytes(arsc[off+12 : off+12+256])
            name = name_bytes.decode("utf-16-le", errors="replace").rstrip("\x00")
            print(f"  package id=0x{pid:02x} name={name!r}")
            if name == OLD:
                nb = NEW.encode("utf-16-le")
                assert len(nb) <= 254
                arsc[off+12 : off+12+256] = nb + b"\x00" * (256 - len(nb))
                patched += 1
                print(f"    -> PATCHED to {NEW!r}")
        if csize == 0: break
        off += csize
    print(f"patched packages: {patched}")
    assert patched >= 1, "no package entry patched!"

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST, "w") as zout:
        for info in zin.infolist():
            data = bytes(arsc) if info.filename == "resources.arsc" else zin.read(info.filename)
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.extra = info.extra
            zout.writestr(ni, data)
    print(f"rebuilt -> {DST} ({os.path.getsize(DST):,} bytes)")

if __name__ == "__main__":
    sys.exit(main())
