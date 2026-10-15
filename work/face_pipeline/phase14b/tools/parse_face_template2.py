# -*- coding: utf-8 -*-
"""parse_face_template2.py — full structural decode of FaceTemplate.bin.
Finds the 140 row boundaries via sequential row-id scan, extracts per-row
payloads, reports zero-rows (identity candidates) and EA rows (13-18)."""
import json, struct

raw = open(r'D:\FL26_Mod\work\face_pipeline\phase14b\tools\FaceTemplate.bin', 'rb').read()
off = 0
fam_n, = struct.unpack_from('<I', raw, off); off += 4
fams = []
for _ in range(fam_n):
    a, b = struct.unpack_from('<HI', raw, off); off += 6
    fams.append((a, b))
total, = struct.unpack_from('<I', raw, off); off += 4
sub, = struct.unpack_from('<H', raw, off); off += 2
pcount, = struct.unpack_from('<I', raw, off); off += 4

# scan: assume each row = (u16 row_id) + payload; find rows by id sequence 0..139
ids_pos = {}
cursor = off
row_marks = []
while cursor < len(raw) - 1:
    v, = struct.unpack_from('<H', raw, cursor)
    if v == len(row_marks) and len(row_marks) < 140:
        row_marks.append((v, cursor))
        cursor += 2
    else:
        cursor += 1
print('sequential row-id marks found:', len(row_marks))
if len(row_marks) >= 2:
    offs = [p for _, p in row_marks]
    gaps = [offs[i+1] - offs[i] for i in range(len(offs)-1)]
    from collections import Counter
    print('row gap distribution:', Counter(gaps).most_common(6))

# hypothesis: rows are contiguous blocks: row_i = [id u16][payload P bytes]
# derive P from the LAST row: last row id 139 at position X, remaining = len - X
last_id, last_pos = row_marks[-1] if row_marks else (None, None)
rem = len(raw) - last_pos
print('last row at %d, remaining %d bytes' % (last_pos, rem))
if len(row_marks) == 140:
    payload = rem - 2
    print('=> payload per row = %d bytes (if uniform)' % payload)
    # extract each row: id u16 + payload
    rows = {}
    for (rid, pos) in row_marks:
        rows[rid] = raw[pos+2:pos+2+payload]
    # zero-rows: payload all zero = identity candidate
    zrows = [i for i in range(140) if not any(rows[i])]
    print('all-zero payload rows (identity candidates):', zrows[:20])
    # EA rows 13-18 payload summaries
    for i in range(13, 19):
        pl = rows[i]
        nz = sum(1 for b in pl if b)
        print('row %3d: nonzero bytes %d/%d | sum %d | head %s' % (i, nz, len(pl), sum(pl), pl[:12].hex()))
    json.dump({'rows_hex': {str(i): rows[i].hex() for i in range(140)},
               'payload_bytes': payload, 'data_offset': off},
              open(r'D:\FL26_Mod\work\face_pipeline\phase14b\tools\face_template_rows.json', 'w'))
    print('rows json saved')
PYEOF_MARKER = None
