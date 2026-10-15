# -*- coding: utf-8 -*-
"""
ClubPlayer deep analysis - figure out the real record format.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

print(f"ClubPlayer: {len(raw)} bytes")
count = struct.unpack_from("<I", raw, 0)[0]
print(f"Count (first uint32): {count}")
print(f"Bytes per record if {count} records: {len(raw) / count:.1f}")
print(f"Expected record size: {(len(raw) - 4) / count:.1f} bytes")

# Show first record in detail
print(f"\nFirst record bytes (0-100):")
for i in range(0, min(100, len(raw)), 16):
    hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, len(raw)-i)))
    ascii_str = ''.join(chr(raw[i+j]) if 32 <= raw[i+j] < 127 else '.' for j in range(min(16, len(raw)-i)))
    print(f"  {i:4x}: {hex_str:<48s} {ascii_str}")

# Try to find player names (UTF-16LE) in the data
# Known: pid 100242 at 0x8575
print(f"\nContext around pid 100242 (offset 0x8575):")
start = 0x8560
for i in range(start, start + 80, 16):
    hex_str = ' '.join(f'{raw[i+j]:02x}' for j in range(min(16, len(raw)-i)))
    print(f"  {i:4x}: {hex_str}")
    # Try to decode as UTF-16
    try:
        text = raw[i:i+32].decode('utf-16-le', errors='replace')
        if any(c.isalpha() for c in text):
            print(f"        UTF-16: {text}")
    except:
        pass

# Find 'Reno' (pid 100373) in UTF-16
reno_utf16 = 'Reno'.encode('utf-16-le')
idx = raw.find(reno_utf16)
print(f"\n'Reno' (UTF-16LE) found at offset: 0x{idx:x}" if idx >= 0 else "'Reno' not found as UTF-16")

# Find 'Vinicius' 
vin_utf16 = 'Vinicius'.encode('utf-16-le')
idx = raw.find(vin_utf16)
print(f"'Vinicius' (UTF-16LE) found at offset: 0x{idx:x}" if idx >= 0 else "'Vinicius' not found")

# Try alternative: maybe records have name inline
# Let's look for ASCII or UTF-16 names
print(f"\nSearching for UTF-16LE strings...")
found = 0
for i in range(4, min(2000, len(raw)-4), 2):
    try:
        # Check if we have a length-prefixed UTF-16 string
        ln = struct.unpack_from("<H", raw, i)[0]
        if 2 <= ln <= 30:
            text = raw[i+2:i+2+ln*2].decode('utf-16-le', errors='strict')
            if all(c.isalpha() or c in '. \'' for c in text):
                print(f"  Offset 0x{i:x}: len={ln} '{text}'")
                found += 1
                if found > 20:
                    break
    except:
        pass

# Alternative: maybe ClubPlayer has a different structure
# Let's check if it's length-prefixed records
print(f"\nTrying alternative: length-prefixed records")
off = 4
rec_num = 0
while off < len(raw) and rec_num < 5:
    rec_len = struct.unpack_from("<I", raw, off)[0]
    if 0 < rec_len < 1000:
        print(f"  Record {rec_num}: offset=0x{off:x} len={rec_len}")
        # Show first 32 bytes of record
        rec_data = raw[off+4:off+4+min(rec_len, 32)]
        hex_str = ' '.join(f'{b:02x}' for b in rec_data)
        print(f"    Data: {hex_str}")
        off += 4 + rec_len
        rec_num += 1
    else:
        break
