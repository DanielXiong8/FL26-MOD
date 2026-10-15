import re
with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\libil2cpp.so', 'rb') as f:
    data = f.read()

# Search for strings containing path-like patterns
keywords = [b'ImageSave', b'SavePath', b'ImagePath', b'IconPath', 
            b'PlayerIcon', b'player_icon', b'PlayerImage', b'player_image',
            b'Portrait', b'portrait', b'HeadIcon', b'head_icon',
            b'FaceIcon', b'face_icon', b'Avatar', b'avatar',
            b'CalculateImageSavePath', b'EditablePlayerIcon',
            b'/Images/', b'/Icons/', b'/Players/', b'/Player/',
            b'/images/', b'/icons/', b'/players/', b'/player/',
            b'Images/', b'Icons/', b'Players/', b'Player/']

found = set()
for kw in keywords:
    for m in re.finditer(b'[\x20-\x7e]{0,100}' + re.escape(kw) + b'[\x20-\x7e]{0,100}', data):
        s = m.group().decode('ascii', errors='replace').strip()
        if 5 < len(s) < 300:
            found.add(s)

for s in sorted(found):
    print(s)
