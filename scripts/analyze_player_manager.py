# -*- coding: utf-8 -*-
"""
Analyze PlayerManager and player lookup methods.
"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\dump.cs', 'r', encoding='utf-8', errors='replace') as f:
    dump = f.read()

# Find PlayerManager class
idx = dump.find('public class PlayerManager')
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
    
    print("PlayerManager class:")
    print("=" * 60)
    
    # Extract methods
    methods = re.findall(r'(?:public|private|protected|internal)\s+(?:static\s+)?(?:virtual\s+)?(?:override\s+)?[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)', class_body)
    print(f"Methods ({len(set(methods))}):")
    for m in sorted(set(methods)):
        if not m.startswith('get_') and not m.startswith('set_'):
            print(f"  {m}")
    
    # Find fields
    fields = re.findall(r'(?:public|private|protected|internal)\s+[\w<>\[\],\s]+\s+(\w+);\s*//\s*0x[0-9A-Fa-f]+', class_body)
    print(f"\nFields:")
    for f in fields[:20]:
        print(f"  {f}")

# Find ClubPlayer class
print("\n" + "=" * 60)
print("ClubPlayer class:")
print("=" * 60)
idx = dump.find('public class ClubPlayer')
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
    
    # Extract properties and fields
    props = re.findall(r'public\s+[\w<>\[\],\s]+\s+(\w+)\s*{\s*get', class_body)
    print(f"Properties: {props[:20]}")
    
    fields = re.findall(r'(?:public|private|protected|internal)\s+[\w<>\[\],\s]+\s+(\w+);\s*//\s*0x[0-9A-Fa-f]+', class_body)
    print(f"Fields: {fields[:20]}")

# Find how ClubPlayer is loaded
print("\n" + "=" * 60)
print("ClubPlayer loading:")
print("=" * 60)
# Search for methods that return ClubPlayer or load ClubPlayer
patterns = [
    r'public\s+.*LoadClubPlayer.*\(.*',
    r'public\s+.*GetClubPlayer.*\(.*',
    r'ClubPlayer\s+GetClubPlayer.*\(.*',
    r'ClubPlayer\[\]\s+.*\(.*',
]
for pat in patterns:
    matches = list(re.finditer(pat, dump))
    print(f"\nPattern '{pat}': {len(matches)} matches")
    for m in matches[:5]:
        start = max(0, m.start() - 100)
        end = min(len(dump), m.end() + 200)
        print(f"  {dump[start:end][:200]}")
