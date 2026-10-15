import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\stringliteral.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

out = []
for item in data:
    s = item.get('value', '')
    if not s or len(s) > 300:
        continue
    addr = item.get('address', '?')
    # Strings with path separators AND (image ext or format specifier)
    if ('/' in s or '\\' in s) and ('.png' in s or '.jpg' in s or '.jpeg' in s or '.webp' in s or '{0}' in s or '%d' in s or '%s' in s):
        out.append(f'[{addr}]: {s!r}')
    # Also search for EditablePlayer/ExternalData
    if 'editableplayer' in s.lower() or 'externaldata' in s.lower():
        out.append(f'[{addr}]: {s!r} (EDITABLE)')

# Also strings near key addresses
out.append("\n=== Near ProfilePic/Texture addresses ===")
for item in data:
    s = item.get('value', '')
    addr = item.get('address', '0x0')
    if isinstance(addr, str):
        try:
            a = int(addr, 16)
            if 0x34E1200 <= a <= 0x34E1600:
                out.append(f'[{addr}]: {s!r}')
        except:
            pass

with open(r'C:\FL26_Mod\saves\path_strings.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f'wrote {len(out)} strings')
