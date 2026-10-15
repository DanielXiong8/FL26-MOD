import json
with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\stringliteral.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f'total string literals: {len(data)}')

for item in data:
    s = item.get('value', '')
    if not s:
        continue
    sl = s.lower()
    if any(k in sl for k in ['image', 'icon', 'photo', 'avatar', 'face', 'head', 'portrait',
                               '.png', '.jpg', '.jpeg', 'savepath', 'imagepath', 'imagesave',
                               'editable', 'custom']):
        if len(s) < 300 and not any(x in s for x in ['System.', 'UnityEngine.', 'Mono.', 'Microsoft', 'http']):
            addr = item.get('address', '?')
            print(f'  [{addr}]: {s}')
