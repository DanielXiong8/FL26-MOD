import UnityPy
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

modified = r'C:\FL26_Mod\modified\assets_bundles_gamedata.unity3d'
if os.path.exists(modified):
    env = UnityPy.load(modified)
    for obj in env.objects:
        if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
            data = obj.read().m_Script
            data_bytes = data.encode('utf-8', errors='replace') if isinstance(data, str) else data
            print(f'Modified Players: {len(data_bytes)} bytes')
            print(f'Magic: {data_bytes[:8].decode("ascii", errors="replace")}')
            orig_env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
            for obj2 in orig_env.objects:
                if obj2.type.name == 'TextAsset' and obj2.read().m_Name == 'Players':
                    orig_data = obj2.read().m_Script
                    orig_bytes = orig_data.encode('utf-8', errors='replace') if isinstance(orig_data, str) else orig_data
                    print(f'Original Players: {len(orig_bytes)} bytes')
                    if len(data_bytes) == len(orig_bytes):
                        print('SAME SIZE - no modification detected')
                    else:
                        print(f'DIFFERENT SIZE (delta={len(data_bytes)-len(orig_bytes)})')
                    break
            break
else:
    print('Modified bundle not found')
