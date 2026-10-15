# -*- coding: utf-8 -*-
"""
Full dump of GlobalTables TextAsset - the FaceTextureID -> texture mapping.
Also check the structure to understand how to ADD a custom entry.
"""
import sys, io, os, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'

env = UnityPy.load(GAMEDATA)
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'GlobalTables':
            raw = d.m_Script
            if isinstance(raw, str):
                raw = raw.encode('utf-8', errors='surrogateescape')
            raw = bytes(raw)
            # dump full hex + text
            print(f"=== GlobalTables ({len(raw)} bytes) ===")
            # print as hex with ASCII
            for i in range(0, len(raw), 64):
                chunk = raw[i:i+64]
                hex_part = ' '.join(f'{b:02x}' for b in chunk)
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print(f"{i:04x}: {hex_part:<64}  {ascii_part}")
            break