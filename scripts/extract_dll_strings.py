import re, sys

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\DummyDll\Assembly-CSharp.dll', 'rb') as f:
    data = f.read()

# Extract UTF-16LE strings (null-terminated, min 4 chars)
found = set()
i = 0
while i < len(data) - 2:
    # Check if this looks like start of UTF-16LE string
    if 32 <= data[i] < 127 and data[i+1] == 0:
        j = i
        while j < len(data) - 1 and ((32 <= data[j] < 127 and data[j+1] == 0) or data[j] >= 0x80):
            j += 2
        if j > i + 6:  # at least 3 chars
            s = data[i:j].decode('utf-16-le', errors='replace').rstrip('\x00')
            if len(s) >= 4:
                found.add(s)
        i = j + 2
    else:
        i += 1

# Filter for path-like or icon-related strings
keywords = ['path', 'save', 'image', 'icon', 'photo', 'avatar', 'face', 'head',
            'portrait', 'texture', 'profile', 'custom', 'editable', 'player',
            '.png', '.jpg', '.jpeg', '/', '\\', 'Camera', 'Gallery', 'camera', 'gallery']

results = []
for s in sorted(found):
    sl = s.lower()
    if any(k.lower() in sl for k in keywords):
        if len(s) < 300 and not any(x in s for x in ['System.', 'UnityEngine.', 'Mono.', 'Microsoft.', 'Google.']):
            results.append(s)

for s in results:
    print(s)
