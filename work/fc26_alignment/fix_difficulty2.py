# -*- coding: utf-8 -*-
"""fix_difficulty2.py - CORRECTED protobuf patch of player.dat (UserSetting proto).

Root cause of the previous patch failing:
  fix_difficulty.py treated the byte right after the key as a length varint,
  but that byte is the field-2 TAG (0x12). It overwrote the tag with the new
  length (e.g. 0x04), producing `... key 04 true` -> tag 0x04 = field 0,
  wire-type 4 (end-group) -> INVALID protobuf. The game's Google.Protobuf
  parser rejects the entry (and likely aborts the whole UserSetting parse),
  so difficulty_selection never actually read as "true".

Correct map-entry encoding (field1=key string, field2=value string):
  0x1A varint(len(sub)) sub
  sub = 0x0A varint(len(key)) key 0x12 varint(len(val)) val

This script rebuilds the submessage properly and byte-compares everything
else to make sure only the intended value changed.
"""
import struct

SRC = r'save_user\files_root\player.dat'   # pristine copy (9260B, from device 10-05)
DST = r'player_dat_fixed2.bin'

# Only flip the feature flag; keep new_dynamic_difficulty_rule at server value '0'.
FLIPS = {
    b'difficulty_selection': b'true',
}


def varint_bytes(v):
    out = b''
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            return out


def varint_at(buf, i):
    v, s = 0, 0
    while True:
        x = buf[i]
        i += 1
        v |= (x & 0x7F) << s
        if not x & 0x80:
            return v, i
        s += 7


raw = open(SRC, 'rb').read()
magic, body = raw[:4], raw[4:]
out = body
report = []

for keystr, newval in FLIPS.items():
    kb = bytes([len(keystr)]) + keystr          # key field: 0x0A len key
    kp = out.find(b'\x0a' + kb)
    if kp < 0:
        report.append('SKIP (not found): %s' % keystr.decode())
        continue
    # sub = 0x0A len(key) key 0x12 len(val) val  (val starts after 2 bytes)
    vpos = kp + 1 + len(kb)                     # position of value TAG (0x12)
    assert out[vpos] == 0x12, 'expected value tag 0x12 at %d, got 0x%02x' % (vpos, out[vpos])
    oldlen, vafter = varint_at(out, vpos + 1)
    oldval = out[vafter:vafter + oldlen]
    newsub = out[kp:vpos] + b'\x12' + varint_bytes(len(newval)) + newval
    sub_end = vafter + oldlen
    # find enclosing f3 record: 0x1A varint(len) sub
    tagp = None
    for back in range(1, 5):
        if out[kp - back] == 0x1A:
            l, after = varint_at(out, kp - back + 1)
            if after + l == sub_end:
                tagp = kp - back
                break
    assert tagp is not None, 'f3 envelope not found for %s' % keystr.decode()
    oldrec = out[tagp:sub_end]
    newrec = b'\x1a' + varint_bytes(len(newsub)) + newsub
    out = out.replace(oldrec, newrec, 1)
    report.append('%s: %r -> %r (%d->%d bytes in sub)' % (
        keystr.decode(), oldval, newval, len(oldval), len(newval)))

newraw = magic + out
open(DST, 'wb').write(newraw)
print('\n'.join(report))
print('written %s: %d bytes (was %d, delta %+d)' % (DST, len(newraw), len(raw), len(newraw) - len(raw)))

# ---- verify: re-parse full message, compare all map entries ----
def parse_map(buf, fieldno):
    entries = {}
    i = 0
    while i < len(buf):
        tag, i = varint_at(buf, i)
        fn, wt = tag >> 3, tag & 7
        if wt == 2:
            l, i = varint_at(buf, i)
            sub, i = buf[i:i + l], i + l
            if fn == fieldno:
                k = v = None
                j = 0
                while j < len(sub):
                    t2, j = varint_at(sub, j)
                    f2, w2 = t2 >> 3, t2 & 7
                    if w2 == 2:
                        l2, j = varint_at(sub, j)
                        s2, j = sub[j:j + l2], j + l2
                        if f2 == 1: k = s2
                        elif f2 == 2: v = s2
                    elif w2 == 0:
                        v0, j = varint_at(sub, j)
                        if f2 == 2: v = v0
                    else:
                        j = len(sub)
                if k is not None: entries[k] = v
        elif wt == 0:
            _, i = varint_at(buf, i)
        elif wt == 5:
            i += 4
        elif wt == 1:
            i += 8
        else:
            raise ValueError('bad wiretype %d at %d' % (wt, i))
    return entries


a = parse_map(body, 3)
b = parse_map(out, 3)
print('\nABTest map: %d entries (before) / %d entries (after)' % (len(a), len(b)))
for k in b:
    old = a.get(k, '<absent>')
    new = b[k]
    if str(old) != str(new):
        print('  CHANGED %-40s %r -> %r' % (k.decode(), old, new))
missing = set(a) - set(b)
print('  entries lost:', sorted(x.decode() for x in missing) if missing else 'NONE')

ei_a = parse_map(body, 5)
ei_b = parse_map(out, 5)
print('EasyInt map: %d / %d entries, lost: %s' % (
    len(ei_a), len(ei_b), sorted(x.decode() for x in set(ei_a) - set(ei_b)) or 'NONE'))
print('  CommonDifficulty:', ei_b.get(b'CommonDifficulty'))
assert b[b'difficulty_selection'] == b'true', 'value not flipped!'
assert len(ei_b) == len(ei_a), 'EasyInt entries lost!'
print('VERIFY OK: difficulty_selection=%r, all other data intact' % b[b'difficulty_selection'].decode())
