# -*- coding: utf-8 -*-
"""
axml_pkg_rename.py — surgical package rename in binary AndroidManifest.xml.
Replaces every string-pool entry STARTING WITH old pkg prefix (covers package attr +
provider authorities + permission names). Rebuilds string pool chunk, fixes sizes.
Only the manifest entry changes inside the APK; all other entries stay byte-identical.
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
    if v > 0x7FFF:
        return struct.pack("<HH", (v >> 16) | 0x8000, v & 0xFFFF)
    return struct.pack("<H", v)

def enc_len8(v):
    if v > 0x7F:
        return bytes([(v >> 8) | 0x80, v & 0xFF])
    return bytes([v])

def parse_pool(b, off):
    ctype, hsize, csize = struct.unpack_from("<HHI", b, off)
    assert ctype == 0x0001, f"not a string pool at {off}: 0x{ctype:04x}"
    scount, stylecount, flags, sstart, styles_start = struct.unpack_from("<IIIII", b, off + 8)
    is_utf8 = bool(flags & UTF8_FLAG)
    offs = [struct.unpack_from("<I", b, off + 28 + i*4)[0] for i in range(scount)]
    strs = []
    base = off + sstart
    for o in offs:
        p = base + o
        if is_utf8:
            _, p = read_len8(b, p)           # utf16 char count (skip)
            blen, p = read_len8(b, p)        # byte length
            s = b[p:p+blen].decode("utf-8", errors="replace")
        else:
            clen, p = read_len16(b, p)
            s = b[p:p+clen*2].decode("utf-16-le", errors="replace")
        strs.append(s)
    return strs, is_utf8, off + csize

def build_pool(strs, is_utf8, stylecount=0):
    blob = bytearray()
    offs = []
    for s in strs:
        offs.append(len(blob))
        if is_utf8:
            eb = s.encode("utf-8")
            blob += enc_len8(len(s)) + enc_len8(len(eb)) + eb + b"\x00"
        else:
            eb = s.encode("utf-16-le")
            blob += enc_len16(len(s)) + eb + b"\x00\x00"
    while len(blob) % 4:
        blob += b"\x00"
    scount = len(strs)
    hsize = 28
    sstart = hsize + scount*4
    csize = sstart + len(blob)
    flags = UTF8_FLAG if is_utf8 else 0
    out = struct.pack("<HHI", 0x0001, hsize, csize)
    out += struct.pack("<IIIII", scount, stylecount, flags, sstart, 0)
    for o in offs:
        out += struct.pack("<I", o)
    out += bytes(blob)
    return out

def patch_manifest(axml: bytes) -> bytes:
    ftype, fhsize, fsize = struct.unpack_from("<HHI", axml, 0)
    assert ftype == 0x0003, "not AXML"
    strs, is_utf8, pool_end = parse_pool(axml, fhsize)
    hits = [(i, s) for i, s in enumerate(strs) if s.startswith(OLD)]
    print(f"strings={len(strs)} utf8={is_utf8} pkg-prefix hits={len(hits)}")
    for i, s in hits:
        print(f"  [{i}] {s!r}")
    new_strs = [(NEW + s[len(OLD):]) if s.startswith(OLD) else s for s in strs]
    pool = build_pool(new_strs, is_utf8)
    rest = axml[pool_end:]
    out = bytearray()
    out += struct.pack("<HHI", ftype, fhsize, fhsize + len(pool) + len(rest))
    out += axml[8:fhsize]
    out += pool
    out += rest
    return bytes(out)

def main():
    with zipfile.ZipFile(SRC) as zf:
        axml = zf.read("AndroidManifest.xml")
    print(f"manifest bytes: {len(axml):,}")
    patched = patch_manifest(axml)
    print(f"patched bytes: {len(patched):,} (delta {len(patched)-len(axml):+d})")
    # self-verify: reparse
    ftype, fhsize, _ = struct.unpack_from("<HHI", patched, 0)
    strs2, _, _ = parse_pool(patched, fhsize)
    assert any(s == NEW for s in strs2), "new package string missing!"
    assert not any(s == OLD for s in strs2), "old bare package still present"
    print("self-verify OK: package string replaced")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST, "w") as zout:
        for info in zin.infolist():
            data = patched if info.filename == "AndroidManifest.xml" else zin.read(info.filename)
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.extra = info.extra
            zout.writestr(ni, data)
    print(f"rebuilt -> {DST} ({os.path.getsize(DST):,} bytes)")

if __name__ == "__main__":
    sys.exit(main())
