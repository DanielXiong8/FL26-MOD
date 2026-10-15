import json
with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\stringliteral.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Search for path patterns and editable/custom related
targets = ['./Texture', 'Texture/face', 'face/', '/face', 'CustomPlayer', 
           'EditablePlayer', 'PlayerIcon', 'playerIcon', 'player_icon',
           'CustomImage', 'CustomFace', 'CustomTexture', 'CustomPhoto',
           'SaveImage', 'LoadImage', 'SaveToFile', 'LoadFromFile',
           'GenProfilePic', 'ProfilePic', 'profile']

for item in data:
    s = item.get('value', '')
    if not s:
        continue
    for t in targets:
        if t.lower() in s.lower():
            addr = item.get('address', '?')
            print(f'  [{addr}]: {s}')
            break
