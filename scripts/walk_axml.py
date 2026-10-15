# -*- coding: utf-8 -*-
"""walk_axml.py — read-only: walk AXML chunk chain, print offset/type/hsize/csize; flag anomalies.
Usage: python walk_axml.py <apk>"""
import struct, sys, zipfile

TYPES = {0x0001: "STRING_POOL", 0x0180: "RES_MAP", 0x0100: "START_NS", 0x0101: "END_NS",
         0x0102: "START_ELEM", 0x0103: "END_ELEM", 0x0104: "TEXT"}

def main(path):
    with zipfile.ZipFile(path) as zf:
        axml = zf.read("AndroidManifest.xml")
    ftype, fhsize, fsize = struct.unpack_from("<HHI", axml, 0)
    print(f"file: type=0x{ftype:04x} hdr={fhsize} size={fsize} actual={len(axml)}")
    off = fhsize
    n = 0
    while off < len(axml) and n < 400:
        if off + 8 > len(axml):
            print(f"  @0x{off:06x} TRUNCATED header (only {len(axml)-off} bytes left)")
            break
        ct, hs, cs = struct.unpack_from("<HHI", axml, off)
        name = TYPES.get(ct, f"?0x{ct:04x}")
        flag = ""
        if hs < 8: flag = " *** BAD hsize ***"
        if cs < 8: flag += " *** BAD csize ***"
        if off + cs > len(axml): flag += f" *** OVERRUNS EOF by {off+cs-len(axml)} ***"
        if n < 8 or flag or ct in (0x0102,):
            extra = ""
            if ct == 0x0102 and hs >= 8 and off + 24 <= len(axml):
                # try to show element name idx
                ni = struct.unpack_from("<i", axml, off + 20)[0]
                extra = f" nameidx={ni}"
            print(f"  @0x{off:06x} {name:<12} hdr=0x{hs:04x} size={cs}{extra}{flag}")
        if cs == 0:
            print("  !! zero-size chunk, stopping walk")
            break
        off += cs
        n += 1
    print(f"walk end: off=0x{off:x} chunks={n} (file 0x{len(axml):x})")

if __name__ == "__main__":
    main(sys.argv[1])
