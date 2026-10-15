# -*- coding: utf-8 -*-
"""
axml_add_activity.py — insert <activity android:name="..." android:exported="true"/> 
as last child of <application> in binary AXML. Also inserts classes10.dex into APK.
Input : build\\base_debuggable2.apk
Output: build\\base_saveexport.apk
"""
import os, struct, sys, zipfile

SRC = r"C:\FL26_Mod\build\base_debuggable2.apk"
DST = r"C:\FL26_Mod\build\base_saveexport.apk"
DEX_SRC = r"C:\FL26_Mod\tools\saveexport\dex\classes.dex"
DEX_NAME = "classes10.dex"

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ACTIVITIES = [
    "com.fl26mod.saveexport.SaveExportActivity",
    "com.fl26mod.saveexport.SaveImportActivity",
    "com.fl26mod.saveexport.TestIconActivity",
    "com.fl26mod.saveexport.PathBruteForceActivity",
    "com.fl26mod.saveexport.FileWatchActivity",
    "com.fl26mod.saveexport.FridaLoaderActivity",
]

UTF8_FLAG = 0x00000100

def read_len16(b, off):
    v = struct.unpack_from("<H", b, off)[0]; off += 2
    if v & 0x8000:
        v = ((v & 0x7FFF) << 16) | struct.unpack_from("<H", b, off)[0]; off += 2
    return v, off

def enc_len16(v):
    return struct.pack("<HH", (v >> 16) | 0x8000, v & 0xFFFF) if v > 0x7FFF else struct.pack("<H", v)

def parse_pool(b, off):
    ctype, hsize, csize = struct.unpack_from("<HHI", b, off)
    assert ctype == 0x0001
    scount, stylecount, flags, sstart, styles_start = struct.unpack_from("<IIIII", b, off + 8)
    is_utf8 = bool(flags & UTF8_FLAG)
    offs = [struct.unpack_from("<I", b, off + 28 + i*4)[0] for i in range(scount)]
    strs = []
    base = off + sstart
    for o in offs:
        p = base + o
        if is_utf8:
            ln = b[p]; p += 1
            if ln & 0x80: ln = ((ln & 0x7F) << 8) | b[p]; p += 1
            blen = b[p]; p += 1
            if blen & 0x80: blen = ((blen & 0x7F) << 8) | b[p]; p += 1
            strs.append(b[p:p+blen].decode("utf-8", errors="replace"))
        else:
            clen, p = read_len16(b, p)
            strs.append(b[p:p+clen*2].decode("utf-16-le", errors="replace"))
    return strs, is_utf8, off + csize

def build_pool(strs, is_utf8):
    blob = bytearray(); offs = []
    for s in strs:
        offs.append(len(blob))
        if is_utf8:
            eb = s.encode("utf-8")
            def enc8(v): return bytes([(v >> 8) | 0x80, v & 0xFF]) if v > 0x7F else bytes([v])
            blob += enc8(len(s)) + enc8(len(eb)) + eb + b"\x00"
        else:
            eb = s.encode("utf-16-le")
            blob += enc_len16(len(s)) + eb + b"\x00\x00"
    while len(blob) % 4: blob += b"\x00"
    scount = len(strs); hsize = 28; sstart = hsize + scount*4; csize = sstart + len(blob)
    out = struct.pack("<HHI", 0x0001, hsize, csize)
    out += struct.pack("<IIIII", scount, 0, UTF8_FLAG if is_utf8 else 0, sstart, 0)
    for o in offs: out += struct.pack("<I", o)
    return out + bytes(blob)

def main():
    with zipfile.ZipFile(SRC) as zf:
        axml = zf.read("AndroidManifest.xml")
    ftype, fhsize, fsize = struct.unpack_from("<HHI", axml, 0)
    assert ftype == 0x0003
    strs, is_utf8, pool_end = parse_pool(axml, fhsize)
    print(f"strings={len(strs)} utf8={is_utf8} pool_end={pool_end}")

    # --- parse resmap ---
    off = pool_end
    ctype, hsize, csize = struct.unpack_from("<HHI", axml, off)
    assert ctype == 0x0180, f"expected resmap at pool_end, got 0x{ctype:04x}"
    resmap_off = off
    n_resmap = (csize - 8) // 4
    resmap = list(struct.unpack_from(f"<{n_resmap}I", axml, off + 8))
    print(f"resource map: {n_resmap} entries")
    off += csize

    # --- resolve string indices ---
    ns_idx = strs.index(ANDROID_NS)
    name_idx = strs.index("name")
    exported_idx = strs.index("exported")
    activity_idx = strs.index("activity")
    application_idx = strs.index("application")
    print(f"ns={ns_idx} name={name_idx} exported={exported_idx} activity={activity_idx} application={application_idx}")

    # --- add class name strings ---
    class_indices = {}
    for cls in ACTIVITIES:
        if cls in strs:
            class_indices[cls] = strs.index(cls)
            print(f"class string already exists: {cls} at idx {class_indices[cls]}")
        else:
            class_indices[cls] = len(strs)
            strs.append(cls)
            print(f"added class string: {cls} at idx {class_indices[cls]}")

    # --- rebuild pool & resmap ---
    new_pool = build_pool(strs, is_utf8)
    need = len(strs)
    new_map = list(resmap) + [0] * (need - len(resmap))
    new_resmap = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(new_map)) + b"".join(struct.pack("<I", v) for v in new_map)

    # --- walk chunks to find </application> END_ELEMENT ---
    # Track depth: <manifest> is depth 0, <application> is depth 1
    cur = off
    depth = 0
    app_end_off = None
    app_found = False
    while cur < len(axml):
        ct, hs, cs = struct.unpack_from("<HHI", axml, cur)
        if ct == 0x0102:  # START_ELEMENT
            name_i = struct.unpack_from("<i", axml, cur + 20)[0]
            if strs[name_i] == "application" and depth == 1:
                app_found = True
            depth += 1
        elif ct == 0x0103:  # END_ELEMENT
            depth -= 1
            name_i = struct.unpack_from("<i", axml, cur + 20)[0]
            if strs[name_i] == "application" and app_found and depth == 1:
                app_end_off = cur
                break
        cur += cs
    assert app_end_off, "no </application> END_ELEMENT found"
    print(f"</application> at 0x{app_end_off:x}")

    # --- build new <activity> elements ---
    new_elements = b""
    for cls in ACTIVITIES:
        class_idx = class_indices[cls]
        # Attribute: android:name = class name (TYPE_STRING=0x03)
        attr_name = struct.pack("<IIi", ns_idx, name_idx, class_idx) + struct.pack("<HBBI", 8, 0, 0x03, class_idx)
        # Attribute: android:exported = true (TYPE_INT_BOOLEAN=0x12)
        attr_exported = struct.pack("<IIi", ns_idx, exported_idx, -1) + struct.pack("<HBBI", 8, 0, 0x12, 0xFFFFFFFF)
        attrs = attr_name + attr_exported

        # START_ELEMENT chunk
        elem_body = struct.pack("<II", 0, 0xFFFFFFFF)  # lineNumber=0, comment=-1
        elem_body += struct.pack("<ii", -1, activity_idx)  # ns=-1, name="activity"
        elem_body += struct.pack("<HHH", 20, 20, 2)  # attrStart=20, attrSize=20, attrCount=2
        elem_body += struct.pack("<HHH", 0, 0, 0)  # idIndex, classIndex, styleIndex
        elem_body += attrs
        elem_cs = 8 + len(elem_body)
        start_elem = struct.pack("<HHI", 0x0102, 16, elem_cs) + elem_body

        # END_ELEMENT chunk
        end_body = struct.pack("<II", 0, 0xFFFFFFFF)
        end_body += struct.pack("<ii", -1, activity_idx)
        end_cs = 8 + len(end_body)
        end_elem = struct.pack("<HHI", 0x0103, 16, end_cs) + end_body

        new_elements += start_elem + end_elem
        print(f"  element for {cls}: {len(start_elem) + len(end_elem)} bytes")

    # --- splice ---
    # Layout: [file hdr] [new pool] [new resmap] [chunks between resmap and app_end] [new element] [app_end onwards]
    between = axml[resmap_off + struct.unpack_from("<I", axml, resmap_off + 4)[0] : app_end_off]
    after = axml[app_end_off:]
    new_body = new_resmap + between + new_elements + after
    total = fhsize + len(new_pool) + len(new_body)
    out = struct.pack("<HHI", 0x0003, fhsize, total) + axml[8:fhsize] + new_pool + new_body

    # --- self-verify: reparse and find all new activities ---
    strs2, _, pe2 = parse_pool(out, fhsize)
    cur2 = pe2
    if struct.unpack_from("<H", out, cur2)[0] == 0x0180:
        cur2 += struct.unpack_from("<I", out, cur2 + 4)[0]
    found_classes = set()
    while cur2 < len(out):
        ct2, hs2, cs2 = struct.unpack_from("<HHI", out, cur2)
        if ct2 == 0x0102:
            name_i2 = struct.unpack_from("<i", out, cur2 + 20)[0]
            if strs2[name_i2] == "activity":
                ac2 = struct.unpack_from("<H", out, cur2 + 28)[0]
                as2 = struct.unpack_from("<H", out, cur2 + 26)[0]
                ast2 = struct.unpack_from("<H", out, cur2 + 24)[0]
                ao = cur2 + 16 + ast2
                for a in range(ac2):
                    nm = struct.unpack_from("<i", out, ao + 4)[0]
                    rv = struct.unpack_from("<i", out, ao + 8)[0]
                    if strs2[nm] == "name" and 0 <= rv < len(strs2):
                        val = strs2[rv]
                        if val in ACTIVITIES:
                            found_classes.add(val)
                            print(f"SELF-VERIFY: found <activity android:name={val!r}>")
                    ao += as2
        cur2 += cs2
    assert len(found_classes) == len(ACTIVITIES), f"self-verify FAILED: found {found_classes}, expected {ACTIVITIES}"
    print("self-verify OK")

    # --- rebuild APK with patched manifest + classes10.dex ---
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST, "w") as zout:
        for info in zin.infolist():
            data = bytes(out) if info.filename == "AndroidManifest.xml" else zin.read(info.filename)
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.extra = info.extra
            zout.writestr(ni, data)
        # add classes10.dex
        with open(DEX_SRC, "rb") as f:
            dex_data = f.read()
        ni = zipfile.ZipInfo(DEX_NAME)
        ni.compress_type = zipfile.ZIP_DEFLATED
        zout.writestr(ni, dex_data)
        # add libfrida-gadget.so to lib/arm64-v8a/
        GADGET = r"C:\FL26_Mod\build\libfrida-gadget.so"
        if os.path.exists(GADGET):
            with open(GADGET, "rb") as f:
                gadget_data = f.read()
            ni = zipfile.ZipInfo("lib/arm64-v8a/libfrida-gadget.so")
            ni.compress_type = zipfile.ZIP_STORED  # so is uncompressed (native libs must be)
            zout.writestr(ni, gadget_data)
            print(f"  added lib/arm64-v8a/libfrida-gadget.so ({len(gadget_data):,} bytes)")
        else:
            print(f"  WARN: {GADGET} not found")
        # add libfrida-gadget.config.so (Frida gadget config)
        GADGET_CFG = r"C:\FL26_Mod\build\libfrida-gadget.config.so"
        if os.path.exists(GADGET_CFG):
            with open(GADGET_CFG, "rb") as f:
                cfg_data = f.read()
            ni = zipfile.ZipInfo("lib/arm64-v8a/libfrida-gadget.config.so")
            ni.compress_type = zipfile.ZIP_STORED
            zout.writestr(ni, cfg_data)
            print(f"  added lib/arm64-v8a/libfrida-gadget.config.so ({len(cfg_data)} bytes)")
    print(f"rebuilt -> {DST} ({os.path.getsize(DST):,} bytes)")

if __name__ == "__main__":
    sys.exit(main())
