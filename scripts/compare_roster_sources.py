# -*- coding: utf-8 -*-
"""
Verify MasterLeaguePlayer as League roster source by checking team 20030 players.
Also check if ClubPlayer Sec2 is the real source by comparing player lists.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Load Players to get names
players_raw = None
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        data = obj.read().m_Script
        players_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

# Parse Players
off = 8
ncnt = struct.unpack_from("<H", players_raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", players_raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", players_raw, off)[0]; off += 4
player_names = {}
for i in range(pcnt):
    pid = struct.unpack_from("<I", players_raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", players_raw, off)[0]; off += 2
    name = players_raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    player_names[pid] = name
    # Skip rest of record
    off += 8 + 3 + 17 + 2 + 1 + 4

# Load MasterLeaguePlayer
mlp_teams = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'MasterLeaguePlayer':
        text = obj.read().m_Script
        for line in text.strip().split('\n'):
            parts = line.strip().split(',')
            if len(parts) >= 2 and parts[1] and parts[0] != 'Teamid':
                tid = int(parts[0])
                pids = [int(p) for p in parts[1].split('|')]
                mlp_teams[tid] = pids
        break

# Load ClubPlayer
club_teams = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        count = struct.unpack_from("<I", raw, 0)[0]
        off = 4 + count * 8
        while off + 17 <= len(raw):
            tid = struct.unpack_from("<I", raw, off)[0]
            pid = struct.unpack_from("<I", raw, off + 4)[0]
            if tid not in club_teams:
                club_teams[tid] = []
            club_teams[tid].append(pid)
            off += 17
        break

# Compare team 20030
TEAM = 20030
print(f"Team {TEAM} comparison:")
print(f"\nMasterLeaguePlayer ({len(mlp_teams.get(TEAM, []))} players):")
for pid in mlp_teams.get(TEAM, []):
    name = player_names.get(pid, '?')
    print(f"  {pid}: {name}")

print(f"\nClubPlayer Sec2 ({len(club_teams.get(TEAM, []))} players):")
for pid in club_teams.get(TEAM, []):
    name = player_names.get(pid, '?')
    print(f"  {pid}: {name}")

# Check which players from MasterLeaguePlayer are in ClubPlayer
mlp_set = set(mlp_teams.get(TEAM, []))
club_set = set(club_teams.get(TEAM, []))
print(f"\nMasterLeaguePlayer players in ClubPlayer: {mlp_set & club_set}")
print(f"MasterLeaguePlayer players NOT in ClubPlayer: {mlp_set - club_set}")
print(f"ClubPlayer players NOT in MasterLeaguePlayer: {len(club_set - mlp_set)}")

# Check a few other teams
print(f"\n--- Other teams ---")
for tid in [20026, 20027, 20028, 20051]:
    mlp = mlp_teams.get(tid, [])
    club = club_teams.get(tid, [])
    print(f"Team {tid}: MLP={len(mlp)} Club={len(club)} overlap={len(set(mlp) & set(club))}")

# Count total players
print(f"\nTotal MasterLeaguePlayer players: {sum(len(p) for p in mlp_teams.values())}")
print(f"Total ClubPlayer players: {sum(len(p) for p in club_teams.values())}")
print(f"MasterLeaguePlayer teams: {len(mlp_teams)}")
print(f"ClubPlayer teams: {len(club_teams)}")
