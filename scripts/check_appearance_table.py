import UnityPy
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        data = obj.read().m_Script
        if isinstance(data, str):
            data_bytes = data.encode('utf-8', errors='replace')
        else:
            data_bytes = data
        print(f'PlayerAppearanceTable: {len(data_bytes)} bytes')
        print(f'First 60 bytes hex: {data_bytes[:60].hex()}')
        # Check if starts with text header
        text_start = data_bytes[:200].decode('utf-8', errors='replace')
        readable = ''.join(c if 32 <= ord(c) < 127 else '.' for c in text_start[:200])
        print(f'Readable: {readable[:200]}')
        
        # Check if CSV format
        if b'\n' in data_bytes[:100]:
            lines = data_bytes.decode('utf-8', errors='replace').split('\n')
            print(f'\nCSV format detected:')
            print(f'  Header: {lines[0][:200]}')
            print(f'  Sample rows:')
            for l in lines[1:5]:
                print(f'    {l[:200]}')
        break
