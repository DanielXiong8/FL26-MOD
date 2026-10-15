import UnityPy
import json
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

out = []

# Read player data TextAssets
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        data = obj.read()
        name = data.m_Name
        if name.isdigit() and int(name) in [1, 20530, 20021, 11076]:
            script = data.m_Script
            out.append(f'=== TextAsset: {name} ===')
            if isinstance(script, str):
                out.append(f'  type: str, len={len(script)}')
                out.append(f'  first 500 chars: {script[:500]}')
            elif isinstance(script, bytes):
                out.append(f'  type: bytes, len={len(script)}')
                out.append(f'  first 200 hex: {script[:200].hex()}')
                try:
                    text = script.decode('utf-8-sig')
                    out.append(f'  decoded: {text[:500]}')
                except:
                    pass
            out.append('')

# Also find all unique TextAsset names that are NOT numbers
out.append('=== Non-numeric TextAssets ===')
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        data = obj.read()
        name = data.m_Name
        if not name.isdigit():
            script = data.m_Script
            size = len(script) if script else 0
            out.append(f'  {name}: {size} chars')

with open(r'C:\FL26_Mod\saves\gamedata_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f'wrote {len(out)} lines')
