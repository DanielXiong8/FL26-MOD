# -*- coding: utf-8 -*-
"""Inspect MasterLeaguePlayer: does it cover team 20030? What does it contain?"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'MasterLeaguePlayer':
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', errors='surrogateescape')
            text = raw.decode('utf-8', errors='replace')
            lines = text.strip().split('\n')
            print(f"total lines: {len(lines)}")
            print("header:", lines[0])
            # teams covered
            teams = {}
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    try:
                        tid = int(parts[0])
                        teams.setdefault(tid, []).append(parts[1])
                    except ValueError:
                        pass
            print(f"teams with entries: {len(teams)}")
            for t in sorted(teams):
                print(f"  team {t}: {len(teams[t])} players")
            if 20030 in teams:
                print(f"\nteam 20030 entries: {teams[20030]}")
            # show a few raw lines
            print("\nsample lines:")
            for l in lines[1:6]:
                print("  ", l)
            break
