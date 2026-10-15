# -*- coding: utf-8 -*-
"""fix_difficulty3.py - corrected patch applied to the CURRENT device player.dat.

player.dat layout (verified):
  [16B header — stable id/nonce, NOT a payload checksum; preserved as-is]
  [envelope protobuf: f3 varint 1 | f4 len-delimited payload = UserSetting message]
  UserSetting: f1 InstallVersion, f2 LoginVersion, f3 ABTest map<string,string>,
               f4 EasyString map, f5 EasyInt map, ...

Edit: ABTest['difficulty_selection'] = "false" -> "true" with a WELL-FORMED
map-entry record:  0x1A <len> | 0x0A <len> key | 0x12 <len> "true"
(The previous fix ate the 0x12 tag, producing field-0/wiretype-4 garbage that
made Google.Protobuf reject the whole message.)
"""
raw = open(r'verify2\player_before.dat', 'rb').read()
DST = r'player_dat_fixed3.bin'

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
assert raw[16] == 0x18 and raw[17] == 0x01 and raw[18] == 0x22, 'envelope prefix mismatch'
plen, pafter = varint_at(raw, 19)
payload = raw[pafter:pafter + plen]
assert pafter + plen == len(raw), 'trailing bytes present: %d' % (len(raw) - pafter - plen)

key = b'difficulty_selection'
kb = bytes([len(key)]) + key
kp = payload.find(b'\x0a' + kb)
assert kp >= 0, 'key not found'
# enclosing map record: 0x1A <varint sublen> sub
tagp = None
for back in range(1, 5):
    if payload[kp - back] == 0x1A:
        l, after = varint_at(payload, kp - back + 1)
        # sub must contain the key and end within a sane distance
        if after <= kp and after + l > kp:
            tagp = kp - back
            sub = payload[after:after + l]
            break
assert tagp is not None, 'envelope tag not found'
vpos = kp + 1 + len(kb)   # kp = pos of 0x0A tag; value tag sits after 0x0A+len+key
assert payload[vpos] == 0x12, 'value tag expected, got 0x%02x' % payload[vpos]
oldlen, vafter = varint_at(payload, vpos + 1)
oldval = payload[vafter:vafter + oldlen]
assert oldval == b'false', 'unexpected old value %r' % oldval

newsub = payload[after:vpos] + b'\x12' + varint_bytes(4) + b'true'  # key part + well-formed value
newrec = b'\x1a' + varint_bytes(len(newsub)) + newsub
oldrec = payload[tagp:after + l]
assert oldrec in payload
newpayload = payload.replace(oldrec, newrec, 1)
print('entry: %d bytes -> %d bytes' % (len(oldrec), len(newrec)))

newraw = header + b'\x18\x01\x22' + varint_bytes(len(newpayload)) + newpayload
open(DST, 'wb').write(newraw)
print('written %s: %d bytes (was %d)' % (DST, len(newraw), len(raw)))

# ---- verify ----
def fields_of(buf):
    i = 0; out = []
    while i < len(buf):
        tag, i = varint_at(buf, i)
        fn, wt = tag >> 3, tag & 7
        if fn == 0 or wt in (3, 4):
            raise ValueError('bad tag 0x%02x' % tag)
        if wt == 0:
            v, i = varint_at(buf, i); out.append((fn, wt, v))
        elif wt == 2:
            l2, i = varint_at(buf, i); out.append((fn, wt, buf[i:i+l2])); i += l2
        elif wt == 5: out.append((fn, wt, buf[i:i+4])); i += 4
        elif wt == 1: out.append((fn, wt, buf[i:i+8])); i += 8
    return out

env = fields_of(newraw[16:])
pl = [v for f, w, v in env if f == 4][0]
us = fields_of(pl)
def entries(recs):
    out = {}
    for f, wt, pay in recs:
        if wt != 2: continue
        k = None; val = None; empty = True
        for f2, w2, v2 in fields_of(pay):
            if f2 == 1: k = v2
            elif f2 == 2: val = v2; empty = False
        if k is not None: out[k] = val if not empty else '<empty(=0)>'
    return out
ab_new = entries([r for r in us if r[0] == 3])
ab_old = entries([r for r in fields_of(payload) if r[0] == 3])
ei_new = entries([r for r in us if r[0] == 5])
print('ABTest: %d -> %d entries' % (len(ab_old), len(ab_new)))
diff = {k: (ab_old.get(k), ab_new.get(k)) for k in set(ab_old) | set(ab_new) if ab_old.get(k) != ab_new.get(k)}
print('diffs:', {k.decode(): (str(a), str(b)) for k, (a, b) in diff.items()})
print('difficulty_selection now =', ab_new[b'difficulty_selection'])
print('EasyInt entries:', len(ei_new), '| CommonDifficulty =', ei_new.get(b'CommonDifficulty'))
assert ab_new[b'difficulty_selection'] == b'true'
assert len(ab_new) == len(ab_old) and len(ei_new) == 30
print('VERIFY OK')
