# -*- coding: utf-8 -*-
"""Find team IDs for visible Premier League teams."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Teams table is CSV: id,name,league,country,appearanceID,descNamesID
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Teams':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        text = raw.decode('utf-8', errors='replace')
        lines = text.strip().split('\n')
        print(f"Teams CSV: {len(lines)} lines")
        print(f"Header: {lines[0]}")

        # Find Premier League teams
        targets = ['Arsenal', 'Chelsea', 'Liverpool', 'Manchester City', 'Manchester United',
                   'Newcastle', 'Tottenham', 'Aston Villa', 'Brighton', 'Brentford',
                   'Ipswich', 'Southampton', 'West Ham', 'Everton', 'Bournemouth',
                   'Wolves', 'Nottingham', 'Fulham', 'Crystal Palace', 'Leicester']
        for line in lines[1:]:
            parts = line.split(',')
            if len(parts) >= 3 and parts[2] == 'EnglishLeagueA':
                for t in targets:
                    if t.lower() in parts[1].lower():
                        print(f"  id={parts[0]} name={parts[1]} league={parts[2]} country={parts[3]}")
                        break
        break

# Also check ClubPlayer for team with most players (likely the ones shown in game)
print("\n" + "=" * 60)
print("ClubPlayer: teams with most players")
print("=" * 60)

import struct
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        data = obj.read().m_Script
        raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data

        # Parse section 1: count(4) + [team_id(4) + player_count(4)]
        count = struct.unpack_from("<I", raw, 0)[0]
        print(f"Section 1 entries: {count}")
        off = 4
        teams = []
        for i in range(count):
            tid = struct.unpack_from("<I", raw, off)[0]
            cnt = struct.unpack_from("<I", raw, off + 4)[0]
            teams.append((tid, cnt))
            off += 8

        # Find teams with most players
        teams.sort(key=lambda x: x[1], reverse=True)
        print(f"\nTop 20 teams by player count:")
        for tid, cnt in teams[:20]:
            print(f"  team_id={tid} players={cnt}")

        # Find team 20026
        for tid, cnt in teams:
            if tid == 20026:
                print(f"\n  Team 20026 (Fulham): {cnt} players")
        break
