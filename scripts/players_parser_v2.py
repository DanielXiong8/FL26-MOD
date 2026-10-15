# -*- coding: utf-8 -*-
"""
players_parser_v2.py — Fixed plyrcsv0 parser.
Correctly handles: header(8) → country table → player count(4) → player records.
Each record: pid(4) + name_len(2) + name(UTF-16LE) + fa(2) + fb(2) + fc(2) + nat(2)
             + b1(1) + b16(1) + b0(1) + attrs(17) + tail16(2) + tail8(1) + year(4)
"""
import struct, sys, io, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def parse_plyrcsv0(raw: bytes):
    """Parse plyrcsv0 binary format. Returns (nations, records, total_size)."""
    assert raw[:8] == b"plyrcsv0", f"bad magic: {raw[:8]}"
    off = 8

    # Country name table
    ncnt = struct.unpack_from("<H", raw, off)[0]; off += 2
    nations = []
    for _ in range(ncnt):
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2

    # Player count
    pcnt = struct.unpack_from("<I", raw, off)[0]; off += 4
    print(f"Countries: {ncnt}, Players: {pcnt}")

    # Player records
    recs = []
    for i in range(pcnt):
        start = off
        pid = struct.unpack_from("<I", raw, off)[0]; off += 4
        ln = struct.unpack_from("<H", raw, off)[0]; off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from("<HHHH", raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16 = struct.unpack_from("<H", raw, off)[0]; off += 2
        tail8 = raw[off]; off += 1
        year = struct.unpack_from("<I", raw, off)[0]; off += 4
        recs.append({
            "pid": pid, "name": name, "fa": fa, "fb": fb, "fc": fc, "nat": nat,
            "b1": b1, "b16": b16, "b0": b0, "attrs": attrs,
            "tail16": tail16, "tail8": tail8, "year": year,
            "_offset": start, "_size": off - start
        })

    # Verify 100% consumed
    assert off == len(raw), f"parse not consumed: {off}/{len(raw)} (delta={len(raw)-off})"
    print(f"Parsed {len(recs)} records, 100% consumed ({off}/{len(raw)} bytes)")
    return nations, recs, len(raw)


def serialize_plyrcsv0(nations, recs) -> bytes:
    """Serialize back to plyrcsv0 format. Byte-exact roundtrip."""
    out = io.BytesIO()
    out.write(b"plyrcsv0")
    out.write(struct.pack("<H", len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le')
        out.write(struct.pack("<H", len(nb)//2))
        out.write(nb)
    out.write(struct.pack("<I", len(recs)))
    for r in recs:
        out.write(struct.pack("<I", r["pid"]))
        nb = r["name"].encode('utf-16-le', errors='replace')
        out.write(struct.pack("<H", len(nb)//2))
        out.write(nb)
        out.write(struct.pack("<HHHH", r["fa"], r["fb"], r["fc"], r["nat"]))
        out.write(bytes([r["b1"], r["b16"], r["b0"]]))
        out.write(bytes(r["attrs"]))
        out.write(struct.pack("<H", r["tail16"]))
        out.write(bytes([r["tail8"]]))
        out.write(struct.pack("<I", r["year"]))
    return out.getvalue()


def main():
    import UnityPy
    env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
    raw = None
    for obj in env.objects:
        if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
            data = obj.read().m_Script
            raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
            break

    nations, recs, total = parse_plyrcsv0(raw)

    # Sample 1000 random players
    random.seed(42)
    sample = random.sample(recs, min(1000, len(recs)))
    print(f"\n=== 1000 Random Player Sample ===")
    print(f"Sampled {len(sample)} players")

    # Verify key fields
    valid = 0
    for r in sample:
        if r["pid"] > 0 and len(r["name"]) > 0 and 0 <= r["nat"] < len(nations):
            valid += 1
    print(f"Valid records: {valid}/{len(sample)}")

    # Show first 10
    print(f"\nFirst 10 players:")
    for r in sample[:10]:
        nat_name = nations[r["nat"]] if r["nat"] < len(nations) else "?"
        print(f"  pid={r['pid']} name={r['name']} nat={nat_name} attrs={r['attrs'][:5]}... year={r['year']}")

    # Show last 10
    print(f"\nLast 10 players:")
    for r in sample[-10:]:
        nat_name = nations[r["nat"]] if r["nat"] < len(nations) else "?"
        print(f"  pid={r['pid']} name={r['name']} nat={nat_name} attrs={r['attrs'][:5]}... year={r['year']}")

    # Roundtrip test
    print(f"\n=== Roundtrip Test ===")
    serialized = serialize_plyrcsv0(nations, recs)
    match = serialized == raw
    print(f"Roundtrip byte-exact: {match} ({len(serialized)} vs {len(raw)} bytes)")
    if not match:
        # Find first difference
        for i in range(min(len(serialized), len(raw))):
            if serialized[i] != raw[i]:
                print(f"First diff at offset 0x{i:x}: orig={raw[i]:02x} new={serialized[i]:02x}")
                break

    # Find max player ID
    max_pid = max(r["pid"] for r in recs)
    min_pid = min(r["pid"] for r in recs)
    print(f"\nPlayer ID range: {min_pid} - {max_pid}")

    # Count by nation
    from collections import Counter
    nat_counts = Counter(r["nat"] for r in recs)
    print(f"\nTop 10 nations by player count:")
    for nat_idx, count in nat_counts.most_common(10):
        nat_name = nations[nat_idx] if nat_idx < len(nations) else f"idx{nat_idx}"
        print(f"  {nat_name}: {count} players")

    # Write sample to CSV
    import csv
    with open(r'C:\FL26_Mod\recon\03_player\players_parser_v2_test.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['pid', 'name', 'nation', 'position', 'year', 'balance', 'reaction', 'acceleration', 'velocity', 'stamina'])
        for r in sample:
            nat_name = nations[r["nat"]] if r["nat"] < len(nations) else "?"
            w.writerow([r['pid'], r['name'], nat_name, r['b1'], r['year']] + r['attrs'][:5])
    print(f"\nWrote {len(sample)} samples to players_parser_v2_test.csv")


if __name__ == '__main__':
    main()
