# -*- coding: utf-8 -*-
import math, sys
from collections import Counter

data = open(r"C:\FL26_Mod\extracted\runtime_2000000.hl", "rb").read()
c = Counter(data[:200000])
ent = -sum((n/200000)*math.log2(n/200000) for n in c.values())
print(f"entropy(first 200KB): {ent:.2f} bits/byte (8.0=random/encrypted/compressed)")

sigs = [(b"\x78\x9c", "zlib"), (b"\x78\xda", "zlib-best"), (b"\x1f\x8b", "gzip"),
        (b"\x04\x22\x4d\x18", "lz4-frame"), (b"SQLite format 3", "sqlite"),
        (b"plyrcsv0", "plyrcsv0"), (b'{"', "json"), (b"PK\x03\x04", "zip"),
        (b"FlatBuffers", "flatbuffers-str")]
for sig, name in sigs:
    idx = data.find(sig)
    tag = ("@" + str(idx)) if idx >= 0 else "no"
    print(f"{name:>14}: {tag}")

# how about utf16 names (game uses utf16 in plyrcsv0)
for pat in ["Rano", "Jerez", "Fulham", "Tamacaz"]:
    p16 = pat.encode("utf-16-le")
    idx = data.find(p16)
    print(f"utf16 {pat!r}: {'@'+str(idx) if idx>=0 else 'no'}")
