# -*- coding: utf-8 -*-
"""patch_difficulty_nop.py - re-apply the difficulty fix to a game APK.

Background
----------
libil2cpp.so (0.2.13) contains this logic inside AIConfig GenerateAIConfig():

    blr  <matchManager.Difficulty()>     -> s0 = tier-dependent difficulty float
    cmp  w23, #0                          ; w23 = (some EasyInt setting < 1) && (miniGameId != 6)
    fmov s1, wzr                          ; s1 = 0.0
    fcsel s0, s0, s1, eq                  ; <-- forces match_difficult = 0.0 when the gate trips
    str  s0, [x20, #0x18]                 ; AIConfig.match_difficult

On the device this gate evaluated true, so the AI difficulty sent to the match
engine (libfootball.so) was always 0.0 = Beginner, no matter what tier the
player selected. Replacing the `fcsel` with a NOP keeps the computed difficulty
value unconditionally. Verified working on device (2026-10-10).

File offset (arm64-v8a, libil2cpp.so of the 0.2.13 build):
    0x10E99DC : 00 0c 21 1e  (fcsel s0, s0, s1, eq)  ->  1f 20 03 d5 (nop)

Usage:
    python patch_difficulty_nop.py <input.apk> <output.apk>
    # then: zipalign -p -f 4 -> apksigner sign -> adb install -r

Re-apply this whenever a game APK is rebuilt (e.g., after new alignment batches)!
"""
import os
import struct
import sys
import zipfile

SO_ENTRY = 'lib/arm64-v8a/libil2cpp.so'
PATCH_OFF = 0x10E99DC
ORIG = bytes.fromhex('000c211e')   # fcsel s0, s0, s1, eq
NOP = bytes.fromhex('1f2003d5')    # nop


def check_so(so_bytes):
    """Return (status, detail): 'patchable' | 'already-patched' | 'unknown'."""
    cur = so_bytes[PATCH_OFF:PATCH_OFF + 4]
    if cur == ORIG:
        return 'patchable', cur.hex()
    if cur == NOP:
        return 'already-patched', cur.hex()
    return 'unknown', cur.hex()


def patch_apk(src, dst):
    with zipfile.ZipFile(src) as zin:
        so = zin.read(SO_ENTRY)
        status, detail = check_so(so)
        print('[check] %s @0x%X = %s -> %s' % (SO_ENTRY, PATCH_OFF, detail, status))
        if status == 'unknown':
            raise SystemExit('ERROR: unexpected bytes at patch offset - wrong game version?')
        if status == 'already-patched':
            print('nothing to do (already patched); regenerating output anyway')
        patched = so[:PATCH_OFF] + NOP + so[PATCH_OFF + 4:]
        with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == SO_ENTRY:
                    data = patched
                ni = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                ni.compress_type = item.compress_type
                ni.external_attr = item.external_attr
                if item.compress_type == zipfile.ZIP_STORED:
                    ni.extra = item.extra
                zout.writestr(ni, data)
    print('written %s (%d bytes)' % (dst, os.path.getsize(dst)))
    print('next: zipalign -p -f 4 %s aligned.apk && apksigner sign --out final.apk aligned.apk' % dst)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    patch_apk(sys.argv[1], sys.argv[2])
