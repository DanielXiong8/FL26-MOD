# -*- coding: utf-8 -*-
"""
Check if PlayerAppearanceTable maps player_id -> appearance data.
"""
import struct, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

env = UnityPy.load(r'C:\FL26_Mod\build\gamedata.unity3d')

# Load Players to get known player IDs
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
known_pids = []
for i in range(pcnt):
    pid = struct.unpack_from("<I", players_raw, off)[0]; off += 4
    ln = struct.unpack_from("<H", players_raw, off)[0]; off += 2
    name = players_raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
    known_pids.append((pid, name))
    off += 8 + 3 + 17 + 2 + 1 + 4

# Check PlayerAppearanceTable
for obj in env.objects:
    if obj.type.name == 'TextAsset' and obj.read().m_Name == 'PlayerAppearanceTable':
        raw = obj.read().m_Script
        if isinstance(raw, str): raw = raw.encode('utf-8', errors='surrogateescape')
        
        # Parse as (id, offset) pairs
        print("Checking if PlayerAppearanceTable maps player_id -> offset:")
        
        # Read all pairs
        pairs = []
        off = 8
        while off + 8 <= len(raw):
            id_val = struct.unpack_from("<I", raw, off)[0]
            offset_val = struct.unpack_from("<I", raw, off + 4)[0]
            pairs.append((id_val, offset_val))
            off += 8
        
        print(f"Total pairs: {len(pairs)}")
        print(f"First 10: {pairs[:10]}")
        print(f"Last 10: {pairs[-10:]}")
        
        # Check if IDs are player IDs
        pair_ids = set(p[0] for p in pairs)
        known_pid_set = set(p[0] for p in known_pids)
        
        print(f"\nPair IDs range: {min(pair_ids)} - {max(pair_ids)}")
        print(f"Known PIDs range: {min(known_pid_set)} - {max(known_pid_set)}")
        print(f"Overlap: {len(pair_ids & known_pid_set)}")
        
        # Check specific known players
        test_pids = [103346, 110947, 103281, 100389]  # Arsenal players
        print(f"\nKnown Arsenal players in table:")
        for pid in test_pids:
            if pid in pair_ids:
                idx = [i for i, p in enumerate(pairs) if p[0] == pid][0]
                print(f"  pid {pid}: index={idx}, offset={pairs[idx][1]}")
            else:
                print(f"  pid {pid}: NOT FOUND")
        
        # Check if our new player 180001 is in table
        print(f"\nNew player 180001 in table: {180001 in pair_ids}")
        
        # If not, we need to add it
        if 180001 not in pair_ids:
            # Find max ID and offset
            max_id = max(pair_ids)
            max_offset = max(p[1] for p in pairs)
            print(f"\nMax ID in table: {max_id}")
            print(f"Max offset: {max_offset}")
            print(f"Need to add: (180001, {max_offset + 1})")
        
        break
