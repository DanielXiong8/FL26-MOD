# -*- coding: utf-8 -*-
"""
Deep dive into Arsenal / London Red (Team 20030) across all gamedata assets,
and analyze IL2CPP methods for League player loading.
"""
import struct, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

print("=" * 60)
print("1. Search Team 20030 across ALL TextAssets in gamedata")
print("=" * 60)

team_id_bytes_le = struct.pack("<I", 20030)
team_id_str = "20030"

for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        name = getattr(d, 'm_Name', '')
        raw = d.m_Script
        if isinstance(raw, str):
            raw_bytes = raw.encode('utf-8', errors='surrogateescape')
        else:
            raw_bytes = bytes(raw)
        
        # Check text match
        has_str = team_id_str.encode('utf-8') in raw_bytes
        # Check binary uint32 LE match
        has_bin = team_id_bytes_le in raw_bytes
        
        if has_str or has_bin:
            print(f"  Asset '{name}': size={len(raw_bytes):,}B str_match={has_str} bin_match={has_bin}")

print("\n" + "=" * 60)
print("2. Check MasterLeaguePlayer for 20030")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'MasterLeaguePlayer':
        text = obj.read().m_Script
        for line in text.strip().split('\n'):
            if line.startswith("20030,"):
                print(f"  MasterLeaguePlayer line: {line}")
        break

print("\n" + "=" * 60)
print("3. Check PlayerAppearanceTable for player presence requirement")
print("=" * 60)
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        print(f"  PlayerAppearanceTable size: {len(raw):,} bytes")
        # Check if 180001 or standard player IDs are indexed
        # Let's check format: is it indexed by player ID?
        # If player_id * 4 or fixed records?
        # Check size / 4:
        print(f"  Size / 4 = {len(raw) / 4} entries (max player ID possible: {len(raw) // 4})")
        print(f"  First 32 bytes hex: {raw[:32].hex()}")
        break

print("\n" + "=" * 60)
print("4. Inspect IL2CPP dump.cs for League / Team loading methods")
print("=" * 60)
with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\dump.cs', 'r', encoding='utf-8', errors='replace') as f:
    dump = f.read()

# Search for methods that get players for a team or load ClubPlayer
patterns = [
    r'public\s+.*GetTeamPlayers\(.*',
    r'public\s+.*GetClubPlayer.*\(.*',
    r'public\s+.*GetPlayersByTeam.*\(.*',
    r'public\s+.*InitLeague.*\(.*',
    r'public\s+.*LoadLeague.*\(.*',
    r'class\s+ClubPlayerManager.*',
    r'class\s+TeamDataManager.*',
    r'class\s+MasterLeaguePlayer.*',
]

for pat in patterns:
    matches = list(re.finditer(pat, dump))
    print(f"Pattern '{pat}': {len(matches)} matches")
    for m in matches[:5]:
        start = max(0, m.start() - 50)
        end = min(len(dump), m.end() + 150)
        snippet = dump[start:end].replace('\n', ' ').strip()
        print(f"    {snippet[:160]}")
