# -*- coding: utf-8 -*-
"""
Analyze ClubPlayer f1/f2/f3 fields by comparing with known player positions.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Load Players to get positions
players_raw = None
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'Players':
        data = obj.read().m_Script
        players_raw = data.encode('utf-8', errors='surrogateescape') if isinstance(data, str) else data
        break

# Parse Players - get position (b1 field)
off = 8
ncnt = struct.unpack_from("<H", players_raw, off)[0]; off += 2
for _ in range(ncnt):
    ln = struct.unpack_from("<H", players_raw, off)[0]; off += 2 + ln*2
pcnt = struct.unpack_from("<I", players_raw, off)[0]; off += 4
player_data = {}
for i in range(pcnt):
    pid = struct.unpack_from("<I", players_raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", players_raw, off)[0]; off += 2
    name = players_raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    fa, fb, fc, nat = struct.unpack_from("<HHHH", players_raw, off); off += 8
    b1, b16, b0 = players_raw[off], players_raw[off+1], players_raw[off+2]; off += 3
    attrs = list(players_raw[off:off+17]); off += 17
    off += 2 + 1 + 4  # tail16 + tail8 + year
    player_data[pid] = {"name": name, "b1": b1, "attrs": attrs}

# Load ClubPlayer
club_data = []
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'ClubPlayer':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        count = struct.unpack_from("<I", raw, 0)[0]
        off = 4 + count * 8
        while off + 17 <= len(raw):
            tid = struct.unpack_from("<I", raw, off)[0]
            pid = struct.unpack_from("<I", raw, off + 4)[0]
            f1 = struct.unpack_from("<I", raw, off + 8)[0]
            f2 = struct.unpack_from("<I", raw, off + 12)[0]
            f3 = raw[off + 16]
            club_data.append({"team_id": tid, "player_id": pid, "f1": f1, "f2": f2, "f3": f3})
            off += 17
        break

# Analyze team 20030 (Arsenal)
print("Team 20030 (Arsenal) players:")
print(f"{'PID':<8} {'Name':<20} {'Pos(b1)':<8} {'f1':<4} {'f2':<6} {'f3':<4}")
print("-" * 60)
for r in club_data:
    if r["team_id"] == 20030:
        pid = r["player_id"]
        pdata = player_data.get(pid, {"name": "?", "b1": 0})
        pos_map = {0: "GK", 1: "DF", 2: "MF", 3: "FW"}
        pos = pos_map.get(pdata["b1"], f"?{pdata['b1']}")
        print(f"{pid:<8} {pdata['name']:<20} {pos:<8} {r['f1']:<4} {r['f2']:<6} {r['f3']:<4}")

# Check if f1 correlates with position
print("\n\nF1 distribution by position:")
from collections import defaultdict
pos_f1 = defaultdict(list)
for r in club_data:
    pid = r["player_id"]
    if pid in player_data:
        pos = player_data[pid]["b1"]
        pos_f1[pos].append(r["f1"])

for pos, f1s in sorted(pos_f1.items()):
    pos_name = {0: "GK", 1: "DF", 2: "MF", 3: "FW"}.get(pos, f"?{pos}")
    print(f"  {pos_name}: f1 range {min(f1s)}-{max(f1s)}, avg {sum(f1s)/len(f1s):.1f}")

# Check f2 patterns
print("\n\nF2 distribution:")
f2_vals = [r["f2"] for r in club_data]
from collections import Counter
f2_count = Counter(f2_vals)
print(f"  Most common f2: {f2_count.most_common(10)}")

# Check f3 patterns
print("\n\nF3 distribution:")
f3_vals = [r["f3"] for r in club_data]
f3_count = Counter(f3_vals)
print(f"  Most common f3: {f3_count.most_common(10)}")
