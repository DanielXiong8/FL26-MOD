import re
with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\libil2cpp.so', 'rb') as f:
    data = f.read()

# Find all strings that contain file path separators
found = set()
for m in re.finditer(b'[\x20-\x7e]{3,}', data):
    s = m.group().decode('ascii', errors='replace')
    # Only strings that look like file paths
    if ('/' in s or '\\' in s) and ('.' in s):
        # Filter out system paths, URLs, and code paths
        if not any(x in s for x in ['http', 'https', 'System.', 'UnityEngine.', 'Microsoft', 'Mono.', 'lib/', 'Modules/', 'Runtime/', 'PlatformDependent', '.h', '.cs', '.cpp', '.dll', '.so']):
            if len(s) < 200:
                found.add(s)

for s in sorted(found):
    print(s)
