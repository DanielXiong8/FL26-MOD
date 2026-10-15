# -*- coding: utf-8 -*-
"""
Search dump.cs for League creation and roster loading methods.
"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\dump.cs', 'r', encoding='utf-8', errors='replace') as f:
    dump = f.read()

# Search for methods that might load League rosters
patterns = [
    (r'public\s+.*CreateLeague.*\(.*', 'CreateLeague'),
    (r'public\s+.*InitLeague.*\(.*', 'InitLeague'),
    (r'public\s+.*SetupLeague.*\(.*', 'SetupLeague'),
    (r'public\s+.*GenerateLeague.*\(.*', 'GenerateLeague'),
    (r'public\s+.*BuildLeague.*\(.*', 'BuildLeague'),
    (r'public\s+.*LeagueData.*\(.*', 'LeagueData'),
    (r'public\s+.*GetLeague.*\(.*', 'GetLeague'),
    (r'class\s+LeagueData.*', 'LeagueData class'),
    (r'class\s+LeagueTeam.*', 'LeagueTeam class'),
    (r'class\s+LeaguePlayer.*', 'LeaguePlayer class'),
    (r'LeaguePlayerManager', 'LeaguePlayerManager'),
]

for pat, desc in patterns:
    matches = list(re.finditer(pat, dump))
    print(f"\n{desc}: {len(matches)} matches")
    for m in matches[:3]:
        start = max(0, m.start() - 100)
        end = min(len(dump), m.end() + 300)
        snippet = dump[start:end].replace('\n', ' ').strip()
        print(f"  {snippet[:250]}")

# Search for ClubPlayer usage in League context
print("\n" + "=" * 60)
print("ClubPlayer + League co-occurrence:")
print("=" * 60)
lines = dump.split('\n')
for i, line in enumerate(lines):
    if 'ClubPlayer' in line and 'League' in line:
        start = max(0, i - 2)
        end = min(len(lines), i + 3)
        for j in range(start, end):
            print(f"  {lines[j]}")
        print()

# Search for TeamDataManager methods
print("\n" + "=" * 60)
print("TeamDataManager methods:")
print("=" * 60)
team_mgr_idx = dump.find('class TeamDataManager')
if team_mgr_idx >= 0:
    # Find the class body
    brace_count = 0
    start = dump.find('{', team_mgr_idx)
    end = start
    for i in range(start, len(dump)):
        if dump[i] == '{':
            brace_count += 1
        elif dump[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    class_body = dump[start:end+1]
    # Find all public methods
    methods = re.findall(r'public\s+\w+\s+(\w+)\s*\(', class_body)
    print(f"Methods: {methods[:30]}")
