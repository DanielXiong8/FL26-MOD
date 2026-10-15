# -*- coding: utf-8 -*-
"""
axml_debuggable.py — add android:debuggable="true" to <application> in binary AXML.
Handles: string pool append ("debuggable"), resource map extension (0x0101000f),
attribute insertion into <application> start-tag. Rebuilds chunk chain.
Input : build\base_renamed.apk  (manifest already package-renamed)
Output: build\base_debuggable.apk
"""
import os, struct, sys, zipfile

SRC = r"C:\FL26_Mod\build\base_renamed2.apk"
DST = r"C:\FL26_Mod\build\base_debuggable2.apk"
ANDROID_NS = "http://schemas.android.com/apk/res/android"
ATTR_NAME = "debuggable"
ATTR_RES_ID = 0x0101000F  # android:attr/debuggable

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
            if ln & 0x80:
                ln = ((ln & 0x7F) << 8) | b[p]; p += 1
            blen = b[p]; p += 1
            if blen & 0x80:
                blen = ((blen & 0x7F) << 8) | b[p]; p += 1
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

    # --- locate resource map chunk (right after pool, type 0x0180) ---
    off = pool_end
    ctype, hsize, csize = struct.unpack_from("<HHI", axml, off)
    resmap = []
    resmap_off = None
    if ctype == 0x0180:
        resmap_off = off
        n = (csize - 8) // 4
        resmap = list(struct.unpack_from(f"<{n}I", axml, off + 8))
        print(f"resource map: {n} entries")
        off += csize
    else:
        print("no resource map chunk (will create one)")

    # --- find <application> start element ---
    app_off = None
    app_attr_count = None
    cur = off
    while cur < len(axml):
        ct, hs, cs = struct.unpack_from("<HHI", axml, cur)
        if ct == 0x0102:  # START_ELEMENT
            name_i = struct.unpack_from("<i", axml, cur + 20)[0]
            if 0 <= name_i < len(strs) and strs[name_i] == "application":
                app_off = cur
                app_attr_count = struct.unpack_from("<H", axml, cur + 28)[0]
                break
        cur += cs
    assert app_off, "no <application> found"
    print(f"<application> at 0x{app_off:x}, attrCount={app_attr_count}")

    # --- check existing debuggable ---
    ns_idx = strs.index(ANDROID_NS)
    if ATTR_NAME in strs:
        dbg_idx = strs.index(ATTR_NAME)
    else:
        dbg_idx = None
    attr_start = struct.unpack_from("<H", axml, app_off + 24)[0]
    attr_size = struct.unpack_from("<H", axml, app_off + 26)[0]
    aoff = app_off + 16 + attr_start
    for a in range(app_attr_count):
        nm = struct.unpack_from("<i", axml, aoff + 4)[0]
        if dbg_idx is not None and nm == dbg_idx:
            print("debuggable already present!")
            return
        aoff += attr_size
    attr_end = aoff  # insertion point (end of attribute array)

    # --- 1. string pool: append "debuggable" ---
    if dbg_idx is None:
        strs.append(ATTR_NAME)
        dbg_idx = len(strs) - 1
    new_pool = build_pool(strs, is_utf8)

    # --- 2. resource map: extend to cover dbg_idx with ATTR_RES_ID ---
    need = dbg_idx + 1
    new_map = list(resmap) + [0] * (need - len(resmap))
    new_map[dbg_idx] = ATTR_RES_ID
    new_resmap = struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(new_map)) + b"".join(struct.pack("<I", v) for v in new_map)

    # --- 3. build new application start-tag with +1 attribute ---
    old_chunk = axml[app_off : app_off + struct.unpack_from("<I", axml, app_off + 4)[0]]
    # parse old chunk
    ct, hs, cs = struct.unpack_from("<HHI", old_chunk, 0)
    line, comment = struct.unpack_from("<II", old_chunk, 8)
    ns, name = struct.unpack_from("<ii", old_chunk, 16)
    astart, asize, acount = struct.unpack_from("<HHH", old_chunk, 24)
    id_i, class_i, style_i = struct.unpack_from("<HHH", old_chunk, 30)
    attrs_blob = old_chunk[16 + astart : 16 + astart + acount * asize]
    # new attribute: ns, name, rawValue=-1, typed{size=8,res0=0,type=INT_BOOLEAN(0x12),data=-1}
    new_attr = struct.pack("<IIi", ns_idx, dbg_idx, -1) + struct.pack("<HBBI", 8, 0, 0x12, 0xFFFFFFFF)
    new_acount = acount + 1
    new_chunk_body = struct.pack("<II", line, comment) + struct.pack("<ii", ns, name)
    new_chunk_body += struct.pack("<HHH", astart, asize, new_acount) + struct.pack("<HHH", id_i, class_i, style_i)
    new_chunk_body += attrs_blob + new_attr
    new_cs = 8 + len(new_chunk_body)  # ResChunk_header(8) + body; was 16+ (bug: double-counted line/comment)
    new_chunk = struct.pack("<HHI", 0x0102, hs, new_cs) + new_chunk_body

    # --- 4. splice everything ---
    before_app = axml[pool_end:app_off]  # resource map will be replaced
    after_app = axml[app_off + cs:]
    if resmap_off is not None:
        # skip old resmap chunk
        _, _, old_rm_size = struct.unpack_from("<HHI", axml, resmap_off)
        before_app = axml[resmap_off + old_rm_size : app_off]
        middle = new_resmap + before_app
    else:
        middle = new_resmap + axml[pool_end:app_off]
    new_body = middle + new_chunk + after_app
    total = fhsize + len(new_pool) + len(new_body)
    out = struct.pack("<HHI", 0x0003, fhsize, total) + axml[8:fhsize] + new_pool + new_body

    # --- 5. self-verify: reparse and find debuggable=true on application ---
    strs2, _, pe2 = parse_pool(out, fhsize)
    cur = pe2
    if struct.unpack_from("<H", out, cur)[0] == 0x0180:
        cur += struct.unpack_from("<I", out, cur + 4)[0]
    found = False
    while cur < len(out):
        ct2, hs2, cs2 = struct.unpack_from("<HHI", out, cur)
        if ct2 == 0x0102:
            name_i = struct.unpack_from("<i", out, cur + 20)[0]
            if strs2[name_i] == "application":
                ac2 = struct.unpack_from("<H", out, cur + 28)[0]
                as2 = struct.unpack_from("<H", out, cur + 26)[0]
                ast2 = struct.unpack_from("<H", out, cur + 24)[0]
                ao = cur + 16 + ast2
                for a in range(ac2):
                    nm = struct.unpack_from("<i", out, ao + 4)[0]
                    dt = out[ao + 15]; dv = struct.unpack_from("<I", out, ao + 16)[0]
                    if strs2[nm] == "debuggable":
                        print(f"SELF-VERIFY: application debuggable type=0x{dt:02x} data=0x{dv:08x}")
                        found = (dt == 0x12 and dv == 0xFFFFFFFF)
                    ao += as2
        cur += cs2
    assert found, "self-verify FAILED"
    print("self-verify OK")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST, "w") as zout:
        for info in zin.infolist():
            data = bytes(out) if info.filename == "AndroidManifest.xml" else zin.read(info.filename)
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.extra = info.extra
            zout.writestr(ni, data)
    print(f"rebuilt -> {DST} ({os.path.getsize(DST):,} bytes)")

if __name__ == "__main__":
    sys.exit(main())
