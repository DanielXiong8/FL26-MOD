# -*- coding: utf-8 -*-
"""Find Arsenal team_id and inject test player into correct team."""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Teams table - search for Arsenal
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Teams':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        text = raw.decode('utf-8', errors='replace')
        lines = text.strip().split('\n')

        # Find all EnglishLeagueA teams
        print("English League A teams:")
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 3:
                # Check if it's an English league team
                if 'EnglishLeagueA' in line or 'english' in line.lower():
                    print(f"  {line[:100]}")
                # Search by name
                for name in ['Arsenal', 'Chelsea', 'Liverpool', 'Manchester City', 'Manchester United',
                            'Fulham', 'Newcastle', 'Tottenham', 'West Ham']:
                    if name.lower() in parts[1].lower():
                        print(f"  >>> id={parts[0]} name={parts[1]} full={line[:100]}")
        break

# Find team_id 20026
print("\n\nSearching for team_id 20026:")
for line in lines[1:]:
    parts = line.split(',')
    if parts[0] == '20026':
        print(f"  FOUND: {line[:150]}")
    if parts[0] in ['20001', '20002', '20003', '20004', '20005']:
        print(f"  Team {parts[0]}: {parts[1]}")

# List first 30 teams to understand ID mapping
print("\n\nFirst 30 teams:")
for line in lines[1:31]:
    parts = line.split(',')
    if len(parts) >= 2:
        print(f"  {parts[0]}: {parts[1]}")
