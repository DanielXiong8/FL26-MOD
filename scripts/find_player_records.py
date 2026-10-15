import UnityPy
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        data = obj.read().m_Script
        if isinstance(data, str):
            data = data.encode('utf-8', errors='replace')
        break

# Search for known player names (UTF-16LE encoded)
names_to_find = ['Mbapp', 'Haaland', 'Messi', 'Ronaldo', 'Bellingham', 'Vinicius', 'Kane']

for name in names_to_find:
    name_bytes = name.encode('utf-16-le')
    idx = data.find(name_bytes)
    if idx >= 0:
        print(f'\n=== Found "{name}" at offset 0x{idx:x} ===')
        # Dump surrounding bytes
        start = max(0, idx - 20)
        end = min(len(data), idx + 200)
        chunk = data[start:end]
        print(f'Context ({start:#x} to {end:#x}):')
        print(f'  hex: {chunk[:100].hex()}')
        # Try to parse record structure around this offset
        # Look backwards for record start (might be preceded by ID + length prefix)
        # Try to read as: id(int32) + name_len(int16) + name(utf16le)
        if idx >= 6:
            rec_start = idx - 6
            rec_id = struct.unpack_from('<i', data, rec_start)[0]
            name_len = struct.unpack_from('<H', data, rec_start+4)[0]
            if name_len*2 == len(name_bytes):
                print(f'  Record structure match: id={rec_id}, name_len={name_len}, name="{name}"')
            else:
                print(f'  name_len={name_len}, expected={len(name_bytes)}')
    else:
        print(f'"{name}" not found')

# Also try to find the end of the country list
# Country names end when we see a pattern that looks like a record start
# Let's scan for the first record-like pattern after offset 0x6c4
print('\n=== Scanning for record start after 0x6c4 ===')
offset = 0x6c4
while offset < min(len(data), 0x1000):
    # Try to read as record: id(int32) + name_len(int16) + name
    if offset + 6 > len(data):
        break
    rec_id = struct.unpack_from('<i', data, offset)[0]
    name_len = struct.unpack_from('<H', data, offset+4)[0]
    if 1 <= rec_id <= 200000 and 1 <= name_len <= 50:
        name_bytes = data[offset+6:offset+6+name_len*2]
        try:
            name = name_bytes.decode('utf-16-le')
            if all(c.isprintable() or c == ' ' for c in name):
                print(f'  Possible record at 0x{offset:x}: id={rec_id}, name="{name}"')
                # Dump 200 bytes after this record
                print(f'  Raw 200 bytes after: {data[offset:offset+200].hex()}')
                break
        except:
            pass
    offset += 1
