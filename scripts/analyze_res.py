import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# res.dat is at assets/data/res.dat in the APK
# Let me extract it and analyze
import zipfile
apk = r'C:\FL26_Mod\build\base_debuggable2.apk'
zf = zipfile.ZipFile(apk)
res_data = zf.read('assets/data/res.dat')

print(f'res.dat size: {len(res_data)} bytes')
print(f'magic: {res_data[:16].hex()}')

# The magic is 0x2457d592 — custom format
# Let's look for patterns that might indicate player records
# Player records might have: name string, stats, appearance IDs

# Search for common player name patterns
import re
# Look for ASCII strings that might be player names
strings = []
i = 0
while i < len(res_data):
    if 32 <= res_data[i] < 127:
        start = i
        while i < len(res_data) and 32 <= res_data[i] < 127:
            i += 1
        s = res_data[start:i].decode('ascii', errors='replace')
        if len(s) >= 4 and any(c.isalpha() for c in s):
            strings.append((start, s))
    i += 1

print(f'\nFound {len(strings)} strings')
# Filter for likely player names (contain common patterns)
name_patterns = ['Mbapp', 'Haaland', 'Messi', 'Ronaldo', 'Neymar', 'Kane', 'Bellingham', 'Vinicius', 'Salah', 'De Bruyne']
for pat in name_patterns:
    matches = [s for s in strings if pat.lower() in s[1].lower()]
    if matches:
        print(f'\n"{pat}" matches:')
        for off, s in matches[:5]:
            print(f'  offset 0x{off:x}: {s}')

# Also check the structure — first few bytes
print(f'\nFirst 64 bytes: {res_data[:64].hex()}')
# Try to parse as header
magic, version, count, data_offset = struct.unpack_from('<IIII', res_data, 0)
print(f'Parsed header: magic=0x{magic:08x} version={version} count={count} data_offset=0x{data_offset:x}')
