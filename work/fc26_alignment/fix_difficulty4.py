# -*- coding: utf-8 -*-
"""fix_difficulty4.py - add EasyInt['friendlyDifficulty'] to player.dat.

Findings driving this patch (from IL2CPP decompilation):
  - Friendly matches read  EasyInt['friendlyDifficulty'] (absent -> default 0 = Beginner)
  - League/Cup matches read EasyInt['CommonDifficulty']   (=3 already, user-controllable)
  - The ABTest flag difficulty_selection is SERVER-owned (re-synced on every launch),
    so we no longer touch it; both read paths work with the server value false.

Input : verify2/player_now2.dat  (current device file, 9309B)
Output: player_dat_fixed4.bin    (+ EasyInt entry only)
"""
raw = open(r'verify2\player_now2.dat', 'rb').read()
DST = r'player_dat_fixed4.bin'
VALUE = 3  # match CommonDifficulty (Professional)

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

header = raw[:16]
assert raw[16] == 0x18 and raw[17] == 0x01 and raw[18] == 0x22, 'envelope prefix'
plen, pafter = varint_at(raw, 19)
payload = raw[pafter:pafter + plen]
assert pafter + plen == len(raw), 'trailing bytes'

key = b'friendlyDifficulty'
assert key not in payload, 'key already present!'
# insertion point: right before the first existing EasyInt (f5) record.
# locate an existing EasyInt entry via its unique key and its f5 tag 0x2A.
anchor = b'CommonDifficulty'
kp = payload.find(anchor)
assert kp > 0
tagp = None
for back in range(2, 6):
    if payload[kp - back] == 0x2A:
        tagp = kp - back
        break
assert tagp is not None, 'EasyInt anchor record not found'

sub = b'\x0a' + varint_bytes(len(key)) + key + b'\x10' + varint_bytes(VALUE)  # 0x10 = field2 varint
newrec = b'\x2a' + varint_bytes(len(sub)) + sub
newpayload = payload[:tagp] + newrec + payload[tagp:]

newraw = header + b'\x18\x01\x22' + varint_bytes(len(newpayload)) + newpayload
open(DST, 'wb').write(newraw)
print('added %d-byte EasyInt record; file %d -> %d bytes' % (len(newrec), len(raw), len(newraw)))

# ---- verify ----
def fields_of(buf):
    i = 0; out = []
    while i < len(buf):
        tag, i = varint_at(buf, i)
        fn, wt = tag >> 3, tag & 7
        if fn == 0 or wt in (3, 4):
            raise ValueError('bad tag 0x%02x' % tag)
        if wt == 0: v, i = varint_at(buf, i); out.append((fn, wt, v))
        elif wt == 2:
            l, i = varint_at(buf, i); out.append((fn, wt, buf[i:i+l])); i += l
        elif wt == 5: out.append((fn, wt, buf[i:i+4])); i += 4
        elif wt == 1: out.append((fn, wt, buf[i:i+8])); i += 8
    return out

env = fields_of(newraw[16:])
pl = [v for f, w, v in env if f == 4][0]
us = fields_of(pl)
def maps(recs, fnum):
    out = {}
    for f, wt, pay in recs:
        if f != fnum or wt != 2: continue
        k = val = None; empty = True
        for f2, w2, v2 in fields_of(pay):
            if f2 == 1: k = v2
            elif f2 == 2: val = v2; empty = False
        if k is not None: out[k] = ('<empty(=0)>' if empty else val)
    return out
ab = maps(us, 3)
ei = maps(us, 5)
print('ABTest: %d entries (difficulty_selection=%r)' % (len(ab), ab.get(b'difficulty_selection')))
print('EasyInt: %d entries | friendlyDifficulty=%r | CommonDifficulty=%r' % (
    len(ei), ei.get(key), ei.get(b'CommonDifficulty')))
assert ei.get(key) == VALUE and len(ei) == 31 and len(ab) == 194
assert ab.get(b'difficulty_selection') == b'false'
print('VERIFY OK')
