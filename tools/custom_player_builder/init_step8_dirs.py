import os

dirs = [
    r'C:\FL26_Mod\recon\03_player',
    r'C:\FL26_Mod\recon\04_team',
    r'C:\FL26_Mod\work\face_pipeline\uv',
    r'C:\FL26_Mod\work\face_pipeline\generated',
    r'C:\FL26_Mod\tools\custom_player_builder',
    r'C:\FL26_Mod\logs'
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"Created: {d}")
