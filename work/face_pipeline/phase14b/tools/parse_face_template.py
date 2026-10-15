# -*- coding: utf-8 -*-
"""parse_face_template.py — structural analysis of FaceTemplate.bin (8310 B).
Per Phase14B §6: no format assumptions — dump header, sections, candidate
offsets/strides, observed ranges. Output: face_template_raw.json.
"""
import json, struct, os

src = r'D:\FL26_Mod\work\face_pipeline\phase14b\tools\FaceTemplate.bin'
raw = open(src, 'rb').read()
out = {'size': len(raw), 'hex_head': raw[:64].hex()}

# hypothesis A: header = count(7) + 7x(id u16, count u32=20) + 140 u32 + 7 u16 + 53 u32
off = 0
fam_count, = struct.unpack_from('<I', raw, off); off += 4
out['h_family_count'] = fam_count
fams = []
for i in range(fam_count):
    a, b = struct.unpack_from('<HI', raw, off); off += 6
    fams.append((a, b))
out['h_family_pairs'] = fams
total, = struct.unpack_from('<I', raw, off); off += 4
out['h_total'] = total
sub, = struct.unpack_from('<H', raw, off); off += 2
out['h_sub'] = sub
pcnt, = struct.unpack_from('<I', raw, off); off += 4
out['h_param_count'] = pcnt
out['data_offset'] = off
rest = len(raw) - off
out['rest_bytes'] = rest
out['rest_per_template'] = rest / total if total else 0
out['rest_per_row_x53'] = rest / (total * pcnt) if total and pcnt else 0

# hypothesis B: rest = total * (2 + pcnt*4)? etc — enumerate plausible strides
cands = []
for per in (53, 106, 212, 159, 212, 424):
    if per and rest % per == 0 and rest // per == total:
        cands.append(('u8x%d' % per if per == 53 else 'mixed', per))
out['stride_candidates_exact'] = cands

# sample the data region as u16 and f32 grids for eyeballing
u16 = struct.unpack_from('<%dH' % (min(rest // 2, 400)), raw, off)
out['data_u16_head'] = list(u16[:60])
f32 = struct.unpack_from('<%df' % (min((rest) // 4, 400)), raw, off)
out['data_f32_head'] = [round(x, 4) for x in f32[:60]]

# if rows are (u16 id? + 53 u16 params) = 108B: total*108 = 15120 ≠ rest; try (2+53*2)=108
# enumerate: rest/total = 58.9 — maybe total rows have variable length; check monotonic u16 runs
# dump first 3 "rows" assuming stride 59*2? Just save the raw for the toolchain.
open(os.path.join(os.path.dirname(src), 'face_template_raw.json'), 'w').write(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ('h_family_count', 'h_family_pairs', 'h_total', 'h_sub', 'h_param_count', 'data_offset', 'rest_bytes', 'rest_per_template', 'stride_candidates_exact')}, indent=1))
print('u16 head:', out['data_u16_head'][:30])
print('f32 head:', out['data_f32_head'][:20])
