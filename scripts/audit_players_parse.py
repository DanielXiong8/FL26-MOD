import UnityPy
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Check modified dir
modified = r'C:\FL26_Mod\modified'
if os.path.exists(modified):
    for f in os.listdir(modified):
        fpath = os.path.join(modified, f)
        size = os.path.getsize(fpath)
        print(f'modified/: {f} ({size:,}B)')
else:
    print('modified/ dir does not exist')

print()
print('=== Players table parse test ===')
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        data = obj.read().m_Script
        if isinstance(data, str):
            data_bytes = data.encode('utf-8', errors='replace')
        else:
            data_bytes = data
        print(f'Players: {len(data_bytes)} bytes')
        try:
            magic = data_bytes[:8].decode('ascii', errors='replace')
        except:
            magic = '?'
        print(f'Magic: {magic}')
        # Count records
        offset = 8
        rec_count = 0
        sample = []
        while offset + 6 <= len(data_bytes) and rec_count < 8:
            try:
                pid = int.from_bytes(data_bytes[offset:offset+4], 'little')
                nlen = int.from_bytes(data_bytes[offset+4:offset+6], 'little')
                if 0 < nlen < 60:
                    name = data_bytes[offset+6:offset+6+nlen*2].decode('utf-16-le', errors='replace')
                    sample.append(f'id={pid} name={name} @0x{offset:x}')
                    offset += 6 + nlen*2
                    rec_count += 1
                else:
                    print(f'  BREAK at 0x{offset:x}: pid={pid} nlen={nlen}')
                    break
            except Exception as e:
                print(f'  ERR at 0x{offset:x}: {e}')
                break
        for s in sample:
            print(f'  {s}')
        print(f'  (parsed {rec_count} records)')
        break
