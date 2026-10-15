import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

players_text = None
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        players_text = obj.read().m_Script
        break

data = players_text.encode('utf-8', errors='replace') if isinstance(players_text, str) else players_text

# Header
print(f'Header: {data[:8].decode("ascii", errors="replace")}')
print(f'Total size: {len(data)} bytes')

# Parse country name table (UTF-16LE after header)
offset = 8
countries = []
count = 0
while count < 50:
    # Read 2-byte length
    if offset + 2 > len(data):
        break
    slen = struct.unpack_from('<H', data, offset)[0]
    offset += 2
    if slen == 0 or slen > 1000:
        break
    name = data[offset:offset+slen*2].decode('utf-16-le', errors='replace')
    offset += slen * 2
    countries.append((offset - slen*2 - 2, slen, name))
    count += 1
    if len(countries) <= 5:
        print(f'Country {len(countries)}: "{name}" at offset 0x{offset - slen*2 - 2:x}')

print(f'\nTotal countries: {len(countries)}')
print(f'After countries: offset 0x{offset:x}')

# Now parse player records
# Look for patterns after country list
# Try reading a few records
print('\n=== First 20 player records (binary) ===')
rec_offset = offset
for i in range(20):
    if rec_offset + 20 > len(data):
        break
    # Try to read record header
    # Common patterns: ID (int32), then name (utf-16le string)
    rec_id = struct.unpack_from('<i', data, rec_offset)[0]
    if rec_id < 0 or rec_id > 500000:
        break
    # Name length
    name_len = struct.unpack_from('<H', data, rec_offset + 4)[0]
    if name_len == 0 or name_len > 100:
        break
    name = data[rec_offset+6:rec_offset+6+name_len*2].decode('utf-16-le', errors='replace')
    print(f'Record {i}: id={rec_id} name="{name}" (name_len={name_len})')
    # Skip past name
    next_offset = rec_offset + 6 + name_len * 2
    # Remaining bytes
    remaining = data[next_offset:next_offset+40]
    print(f'  raw next 40 bytes: {remaining.hex()}')
    rec_offset = next_offset + 4  # skip something
