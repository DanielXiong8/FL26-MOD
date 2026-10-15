import re

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\libil2cpp.so', 'rb') as f:
    data = f.read()

# Search for format strings with {0}, {1}, etc. that look like paths
found = set()
for m in re.finditer(b'[\x20-\x7e]{5,}', data):
    s = m.group().decode('ascii', errors='replace')
    if '{0}' in s or '{1}' in s:
        if not any(x in s for x in ['System.', 'UnityEngine.', 'Mono.', 'Microsoft', 'Newtonsoft']):
            found.add(s)

for s in sorted(found):
    print(s)
