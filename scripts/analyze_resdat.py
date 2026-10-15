# -*- coding: utf-8 -*-
"""Analyze assets/data/res.dat (3.9MB) — candidate live roster source. Read-only."""
import io, re, struct, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def main():
    with zipfile.ZipFile(APK) as zf:
        raw = zf.read("assets/data/res.dat")
    print(f"res.dat size={len(raw):,}")
    print("head hex:", raw[:64].hex(" "))
    print("head ascii:", "".join(chr(c) if 32 <= c < 127 else "." for c in raw[:64]))

    # magic checks
    for sig, name in [(b"SQLite format 3", "sqlite"), (b"plyrcsv0", "plyrcsv0"),
                      (b"PK\x03\x04", "zip"), (b"\x78\x9c", "zlib"), (b"\x1f\x8b", "gzip"),
                      (b"\x04\x22\x4d\x18", "lz4"), (b'{"', "json"), (b"UnityFS", "unityfs")]:
        idx = raw.find(sig)
        print(f"{name:>10}: {'@'+str(idx) if idx>=0 else 'no'}")

    # name probes (utf-8 and utf-16)
    for pat in ["Rano", "Jerez", "Fulham", "Tamacaz", "Dienias", "Earpz"]:
        i8 = raw.find(pat.encode("utf-8"))
        i16 = raw.find(pat.encode("utf-16-le"))
        print(f"  {pat!r}: utf8={'@'+str(i8) if i8>=0 else 'no'} utf16={'@'+str(i16) if i16>=0 else 'no'}")

    # printable string sample (utf-8)
    strs = re.findall(rb"[ -~]{6,}", raw[:400000])[:40]
    print("\nfirst ascii strings:")
    for s in strs:
        print("  ", s.decode("ascii", errors="replace")[:90])

if __name__ == "__main__":
    sys.exit(main())
