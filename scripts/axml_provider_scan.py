# -*- coding: utf-8 -*-
"""
axml_provider_scan.py — parse AXML XML body, find every <provider android:authorities=...>
value, report which ones do NOT start with the package prefix (collision candidates),
and patch ALL authorities to unique values (append .mod where needed).
Input APK: working_ascii\base_poc.apk  ->  build\base_renamed.apk
"""
import os, struct, sys, zipfile

SRC = r"C:\FL26_Mod\working_ascii\base_poc.apk"
DST = r"C:\FL26_Mod\build\base_renamed.apk"
OLD = "com.football.soccer.league"
NEW = "com.football.soccer.league.mod"
UTF8_FLAG = 0x00000100

def read_len16(b, off):
    v = struct.unpack_from("<H", b, off)[0]; off += 2
    if v & 0x8000:
        v = ((v & 0x7FFF) << 16) | struct.unpack_from("<H", b, off)[0]; off += 2
    return v, off

def read_len8(b, off):
    v = b[off]; off += 1
    if v & 0x80:
        v = ((v & 0x7F) << 8) | b[off]; off += 1
    return v, off

def enc_len16(v):
    return struct.pack("<HH", (v >> 16) | 0x8000, v & 0xFFFF) if v > 0x7FFF else struct.pack("<H", v)

def enc_len8(v):
    return bytes([(v >> 8) | 0x80, v & 0xFF]) if v > 0x7F else bytes([v])

def parse_pool(b, off):
    ctype, hsize, csize = struct.unpack_from("<HHI", b, off)
    assert ctype == 0x0001
    scount, stylecount, flags, sstart, _ = struct.unpack_from("<IIIII", b, off + 8)
    is_utf8 = bool(flags & UTF8_FLAG)
    offs = [struct.unpack_from("<I", b, off + 28 + i*4)[0] for i in range(scount)]
    strs = []
    base = off + sstart
    for o in offs:
        p = base + o
        if is_utf8:
            _, p = read_len8(b, p); blen, p = read_len8(b, p)
            s = b[p:p+blen].decode("utf-8", errors="replace")
        else:
            clen, p = read_len16(b, p)
            s = b[p:p+clen*2].decode("utf-16-le", errors="replace")
        strs.append(s)
    return strs, is_utf8, off + csize

def build_pool(strs, is_utf8):
    blob = bytearray(); offs = []
    for s in strs:
        offs.append(len(blob))
        if is_utf8:
            eb = s.encode("utf-8")
            blob += enc_len8(len(s)) + enc_len8(len(eb)) + eb + b"\x00"
        else:
            eb = s.encode("utf-16-le")
            blob += enc_len16(len(s)) + eb + b"\x00\x00"
    while len(blob) % 4: blob += b"\x00"
    scount = len(strs); hsize = 28; sstart = hsize + scount*4; csize = sstart + len(blob)
    out = struct.pack("<HHI", 0x0001, hsize, csize)
    out += struct.pack("<IIIII", scount, 0, UTF8_FLAG if is_utf8 else 0, sstart, 0)
    for o in offs: out += struct.pack("<I", o)
    return out + bytes(blob)

def scan_providers(axml, strs, pool_end):
    """Walk XML body chunks; collect provider/authority string indices."""
    off = pool_end
    auth_idx = strs.index("authorities") if "authorities" in strs else None
    hits = []   # (element_name, authority_string_index, authority_value)
    while off < len(axml):
        ctype, hsize, csize = struct.unpack_from("<HHI", axml, off)
        if ctype == 0x0102:  # START_ELEMENT
            name_i = struct.unpack_from("<i", axml, off + 20)[0]
            elem = strs[name_i] if 0 <= name_i < len(strs) else "?"
            attr_start = struct.unpack_from("<H", axml, off + 24)[0]
            attr_size = struct.unpack_from("<H", axml, off + 26)[0]
            attr_count = struct.unpack_from("<H", axml, off + 28)[0]
            aoff = off + 16 + attr_start
            for a in range(attr_count):
                aname_i = struct.unpack_from("<i", axml, aoff + 4)[0]
                raw_i = struct.unpack_from("<i", axml, aoff + 8)[0]
                dtype = axml[aoff + 15]
                data = struct.unpack_from("<I", axml, aoff + 16)[0]
                if aname_i == auth_idx:
                    sidx = raw_i if raw_i >= 0 else (data if dtype == 0x03 else -1)
                    if 0 <= sidx < len(strs):
                        hits.append((elem, sidx, strs[sidx]))
                aoff += attr_size
        off += csize
    return hits

def main():
    with zipfile.ZipFile(SRC) as zf:
        axml = zf.read("AndroidManifest.xml")
    ftype, fhsize, fsize = struct.unpack_from("<HHI", axml, 0)
    strs, is_utf8, pool_end = parse_pool(axml, fhsize)

    providers = scan_providers(axml, strs, pool_end)
    print(f"provider authority declarations: {len(providers)}")
    patch_set = {}
    for elem, sidx, val in providers:
        mark = "PKG-PREFIX" if val.startswith(OLD) else "**NON-PREFIX**"
        print(f"  <{elem}> [{sidx}] {val}  {mark}")
        if val.startswith(OLD):
            patch_set[sidx] = NEW + val[len(OLD):]
        else:
            patch_set[sidx] = val + ".mod"
    # also catch any remaining package-prefixed strings (package attr, permissions)
    for i, s in enumerate(strs):
        if s.startswith(OLD) and i not in patch_set:
            patch_set[i] = NEW + s[len(OLD):]

    print(f"\ntotal strings to patch: {len(patch_set)}")
    new_strs = [patch_set.get(i, s) for i, s in enumerate(strs)]
    pool = build_pool(new_strs, is_utf8)
    rest = axml[pool_end:]
    out = struct.pack("<HHI", ftype, fhsize, fhsize + len(pool) + len(rest)) + axml[8:fhsize] + pool + rest

    # self verify
    ftype2, fhsize2, _ = struct.unpack_from("<HHI", out, 0)
    strs2, _, pe2 = parse_pool(out, fhsize2)
    prov2 = scan_providers(bytes(out), strs2, pe2)
    bad = [v for _, _, v in prov2 if not (v.startswith(NEW) or v.endswith(".mod"))]
    assert not bad, f"unpatched: {bad}"
    assert not any(s == OLD for s in strs2)
    print("self-verify OK: all authorities unique-ified")

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
