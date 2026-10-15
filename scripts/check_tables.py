import UnityPy
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

out = []

# Check ClubPlayer
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        lines = data.strip().split('\n')
        out.append(f'ClubPlayer: {len(lines)} lines')
        out.append(f'Header: {lines[0]}')
        out.append(f'Sample lines:')
        for l in lines[1:6]:
            out.append(f'  {l[:200]}')
        out.append(f'...')
        for l in lines[-3:]:
            out.append(f'  {l[:200]}')
        out.append('')
        break

# Check PlayerAppearanceTable
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        data = obj.read().m_Script
        lines = data.strip().split('\n')
        out.append(f'PlayerAppearanceTable: {len(lines)} lines')
        out.append(f'Header: {lines[0][:200]}')
        out.append(f'Sample:')
        for l in lines[1:4]:
            out.append(f'  {l[:200]}')
        out.append('')
        break

# Check StarPlayerAppearance
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'StarPlayerAppearance':
        data = obj.read().m_Script
        lines = data.strip().split('\n')
        out.append(f'StarPlayerAppearance: {len(lines)} lines')
        for l in lines[:10]:
            out.append(f'  {l[:200]}')
        out.append('')
        break

with open(r'C:\FL26_Mod\saves\table_structures.txt', 'w', encoding='utf-8', errors='replace') as f:
    f.write('\n'.join(out))
print(f'wrote {len(out)} lines')
print('\n'.join(out))
