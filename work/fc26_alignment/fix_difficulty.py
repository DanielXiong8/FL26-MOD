# -*- coding: utf-8 -*-
"""fix_difficulty.py - flip remote-config flags in player.dat (surgical protobuf edit).
Flags: difficulty_selection=false -> true ; new_dynamic_difficulty_rule=0 -> 1
Structure: [4B magic][protobuf: repeated f3{f1=key, f2=value} + other fields]
Edit is done per-f3-submessage: locate tag(0x1A)+len, rebuild that sub only.
"""
import os

SRC = r'save_user\files_root\player.dat'
DST = r'player_dat_fixed.bin'

raw = open(SRC, 'rb').read()
magic, body = raw[:4], raw[4:]


def varint_bytes(v):
    out = b''
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out += bytes([b | 0x80])
        else:
            out += bytes([b])
            break
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


FLIPS = {
    b'difficulty_selection': b'true',
    b'new_dynamic_difficulty_rule': b'1',
}


def rebuild_sub(body, keystr, newval):
    """locate f3 sub containing key, return (tagpos, oldlenbytes, newsub) or None"""
    kp = body.find(bytes([len(keystr)]) + keystr)
    if kp < 0:
        return None
    tagp = None
    for back in range(2, 7):
        if body[kp - back] == 0x1A:
            tagp = kp - back
            break
    if tagp is None:
        return None
    vlen, after = varint_at(body, tagp + 1)
    sub = body[after:after + vlen]
    kbytes = bytes([len(keystr)]) + keystr
    k2 = sub.find(kbytes)
    if k2 < 0:
        return None
    vpos2 = k2 + len(kbytes)
    l2, va2 = varint_at(sub, vpos2)
    newsub = sub[:vpos2] + varint_bytes(len(newval)) + newval + sub[va2 + l2:]
    return tagp, varint_bytes(vlen), newsub


outbody = body
for keystr, newval in FLIPS.items():
    r = rebuild_sub(outbody, keystr, newval)
    if r is None:
        print('SKIP (not found):', keystr)
        continue
    tagp, oldlenbytes, newsub = r
    oldmsg = bytes([0x1A]) + oldlenbytes + body[tagp + 1 + len(oldlenbytes):tagp + 1 + len(oldlenbytes) + int.from_bytes(oldlenbytes, 'little')]
    newmsg = bytes([0x1A]) + varint_bytes(len(newsub)) + newsub
    assert oldmsg in outbody, 'old msg not contiguous'
    outbody = outbody.replace(oldmsg, newmsg, 1)
    print('patched %s: %s -> %s' % (keystr.decode(), keystr and FLIPS[keystr], newval))

newfile = magic + outbody
open(DST, 'wb').write(newfile)
print('written %s, len %d (orig %d)' % (DST, len(newfile), len(raw)))

# verify
for keystr, expect in [(b'difficulty_selection', b'true'), (b'new_dynamic_difficulty_rule', b'1')]:
    k2 = newfile.find(bytes([len(keystr)]) + keystr)
    l2, va2 = varint_at(newfile, k2 + len(keystr))
    print('verify', keystr.decode(), '=', newfile[va2:va2 + l2])
