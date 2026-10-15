# -*- coding: utf-8 -*-
"""find_images.py — search for image files (PNG/JPEG magic bytes) in game data."""
import os, sys

base = r"C:\FL26_Mod\saves\exported"
# Also check player.dat / player2.dat
dat_files = []
for root, dirs, files in os.walk(base):
    for f in files:
        fp = os.path.join(root, f)
        dat_files.append(fp)

print("=== Checking for image magic bytes ===")
for fp in dat_files:
    try:
        with open(fp, "rb") as f:
            header = f.read(16)
        if header[:4] == b'\x89PNG':
            print(f"PNG: {fp} ({os.path.getsize(fp)}B)")
        elif header[:3] == b'\xff\xd8\xff':
            print(f"JPEG: {fp} ({os.path.getsize(fp)}B)")
        elif header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            print(f"WebP: {fp} ({os.path.getsize(fp)}B)")
        elif header[:4] == b'GIF8':
            print(f"GIF: {fp} ({os.path.getsize(fp)}B)")
        elif header[:2] == b'BM':
            print(f"BMP: {fp} ({os.path.getsize(fp)}B)")
    except:
        pass

# Also check player.dat content
for name in ["player.dat", "player2.dat"]:
    fp = os.path.join(base, "save_export", "Archives", name)
    if not os.path.exists(fp):
        # Try finding it
        for root, dirs, files in os.walk(base):
            if name in files:
                fp = os.path.join(root, name)
                break
    if os.path.exists(fp):
        with open(fp, "rb") as f:
            data = f.read(64)
        print(f"\n{name}: {os.path.getsize(fp)}B, first 64 bytes:")
        print(f"  hex: {data.hex()}")
        print(f"  ascii: {''.join(chr(b) if 32<=b<127 else '.' for b in data)}")

print("\ndone")
