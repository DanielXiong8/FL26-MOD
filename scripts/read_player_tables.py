import UnityPy
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

out = []
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        data = obj.read()
        name = data.m_Name
        if name in ['Players', 'PlayerAppearanceTable', 'ClubPlayer', 'StarPlayerAppearance', 'MasterLeaguePlayer']:
            script = data.m_Script
            out.append(f'=== {name} (len={len(script)}) ===')
            out.append(f'first 800 chars:')
            out.append(script[:800])
            out.append('...')
            out.append(f'last 200 chars:')
            out.append(script[-200:])
            out.append('')

with open(r'C:\FL26_Mod\saves\player_tables.txt', 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(out))
print(f'wrote {len(out)} lines')

# Print preview of Players table
for line in out[:30]:
    print(line)
