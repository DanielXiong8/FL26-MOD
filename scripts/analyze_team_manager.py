# -*- coding: utf-8 -*-
"""
Extract TeamDataManager and related class methods from dump.cs.
"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\dump.cs', 'r', encoding='utf-8', errors='replace') as f:
    dump = f.read()

# Find TeamDataManager class
idx = dump.find('public class TeamDataManager')
if idx >= 0:
    # Find class body
    brace_count = 0
    start = dump.find('{', idx)
    end = start
    for i in range(start, len(dump)):
        if dump[i] == '{':
            brace_count += 1
        elif dump[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    class_body = dump[idx:end+1]
    
    print("TeamDataManager class found:")
    print("=" * 60)
    
    # Extract all method signatures
    methods = re.findall(r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:virtual\s+)?(?:override\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)', class_body)
    print(f"Methods ({len(methods)}):")
    for m in sorted(set(methods)):
        if not m.startswith('get_') and not m.startswith('set_'):
            print(f"  {m}")
    
    # Find GetTeamRosterCap
    if 'GetTeamRosterCap' in class_body:
        idx2 = class_body.find('GetTeamRosterCap')
        print(f"\nGetTeamRosterCap context:")
        print(class_body[max(0,idx2-100):idx2+200])
    
    # Find any method with 'Roster' or 'Player' in name
    print(f"\nRoster/Player related methods:")
    for m in sorted(set(methods)):
        if 'roster' in m.lower() or 'player' in m.lower():
            print(f"  {m}")
            
    # Find fields
    fields = re.findall(r'(?:public|private|protected|internal)\s+[\w<>\[\],\s]+\s+(\w+);\s*//\s*0x[0-9A-Fa-f]+', class_body)
    print(f"\nFields ({len(fields)}):")
    for f in fields[:20]:
        print(f"  {f}")

# Find ClubPlayerDatabase
print("\n" + "=" * 60)
print("ClubPlayerDatabase:")
print("=" * 60)
idx = dump.find('class ClubPlayerDatabase')
if idx >= 0:
    start = dump.find('{', idx)
    end = start
    brace_count = 0
    for i in range(start, len(dump)):
        if dump[i] == '{':
            brace_count += 1
        elif dump[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    class_body = dump[idx:end+1]
    methods = re.findall(r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:virtual\s+)?(?:override\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)', class_body)
    print(f"Methods: {methods}")

# Find how League creates team rosters
print("\n" + "=" * 60)
print("League.CreateLeague method signature:")
print("=" * 60)
matches = re.finditer(r'public\s+.*CreateLeague\s*\([^)]*\)', dump)
for m in matches:
    print(f"  {m.group()}")
    # Show context
    start = max(0, m.start() - 200)
    end = min(len(dump), m.end() + 400)
    print(f"  Context: {dump[start:end][:300]}")
