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

# Vinicius record at offset 0xa75c1
# Parse: id(4) + name_len(2) + name(name_len*2) + ??? (stats/appearance)
# Let's find the record size by looking at the next record start

# First, verify Vinicius record
offset = 0xa75c1
rec_id = struct.unpack_from('<i', data, offset)[0]
name_len = struct.unpack_from('<H', data, offset+4)[0]
name = data[offset+6:offset+6+name_len*2].decode('utf-16-le', errors='replace')
print(f'Verified: id={rec_id}, name_len={name_len}, name="{name}"')
print(f'Name ends at offset 0x{offset+6+name_len*2:x}')

# Find the next record start (next ID)
next_offset = offset + 6 + name_len * 2
print(f'\nNext 100 bytes after name:')
for i in range(0, 100, 4):
    if next_offset + i + 4 > len(data):
        break
    val = struct.unpack_from('<i', data, next_offset + i)[0]
    if 1 <= val <= 200000:
        print(f'  offset +{i}: {val} (possible next record ID)')
    # Also try 2-byte
    val2 = struct.unpack_from('<H', data, next_offset + i)[0]
    if 1 <= val2 <= 100:
        print(f'  offset +{i}: {val2} (possible field)')

# Now let's find the next record by looking for "Ronaldo"
ronaldo_bytes = 'Ronaldo'.encode('utf-16-le')
ronaldo_idx = data.find(ronaldo_bytes, next_offset)
if ronaldo_idx > 0:
    # Ronaldo record starts at ronaldo_idx - 6 (id + name_len before name)
    ronaldo_start = ronaldo_idx - 6
    print(f'\nRonaldo record starts at 0x{ronaldo_start:x}')
    print(f'Record size (Vinicius): 0x{ronaldo_start - offset:x} = {ronaldo_start - offset} bytes')
    
    # Parse Ronaldo record
    rid = struct.unpack_from('<i', data, ronaldo_start)[0]
    rlen = struct.unpack_from('<H', data, ronaldo_start+4)[0]
    rname = data[ronaldo_start+6:ronaldo_start+6+rlen*2].decode('utf-16-le', errors='replace')
    print(f'Ronaldo: id={rid}, name_len={rlen}, name="{rname}"')
    
    # The record size tells us how many bytes are between records
    rec_size = ronaldo_start - offset
    print(f'\n=== Record structure (size={rec_size} bytes) ===')
    print(f'  0-3: id (int32)')
    print(f'  4-5: name_len (int16)')
    print(f'  6-{5+name_len*2}: name (UTF-16LE, {name_len} chars)')
    print(f'  {6+name_len*2}-{rec_size-1}: stats/appearance ({rec_size - 6 - name_len*2} bytes)')
    
    # Parse the stats/appearance section
    stats_offset = offset + 6 + name_len * 2
    stats_size = rec_size - 6 - name_len * 2
    stats = data[stats_offset:stats_offset + stats_size]
    print(f'\n  Stats hex ({stats_size} bytes):')
    for i in range(0, min(stats_size, 100), 2):
        val = struct.unpack_from('<H', stats, i)[0]
        if val > 0:
            print(f'    +{i}: {val} (0x{val:04x})')
