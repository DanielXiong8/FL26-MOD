import re, os, struct, sys
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields

# Check res.dat for ExternalDataSetting protobuf
res_path = r"C:\FL26_Mod\saves\res.dat"
if not os.path.exists(res_path):
    for root, dirs, files in os.walk(r"C:\FL26_Mod\saves"):
        for f in files:
            if f == "res.dat":
                res_path = os.path.join(root, f)
                break

if res_path:
    print(f"res.dat: {res_path} ({os.path.getsize(res_path):,}B)")
    with open(res_path, "rb") as f:
        data = f.read()
    
    # Search for path-like strings in res.dat
    found = set()
    for m in re.finditer(b'[\x20-\x7e]{4,}', data):
        s = m.group().decode('ascii', errors='replace')
        if ('/' in s or '\\' in s) and len(s) < 200:
            if not any(x in s for x in ['http', 'System.', 'UnityEngine.', 'Mono.']):
                found.add(s)
    
    print(f"\n=== Path-like strings in res.dat ===")
    for s in sorted(found):
        print(f"  {s}")
    
    # Try to find ExternalDataSetting protobuf (look for Player type = 50000000 = 0x02FAF080)
    # In protobuf varint: 50000000 = 0x80 0xC0 0xEB 0x97 0x01
    target = bytes([0x80, 0xC0, 0xEB, 0x97, 0x01])
    idx = data.find(target)
    print(f"\n=== Player type (50000000) varint at offset: 0x{idx:x} ===")
    if idx >= 0:
        start = max(0, idx - 20)
        end = min(len(data), idx + 200)
        chunk = data[start:end]
        print(f"context hex: {chunk.hex()}")
        print(f"ascii: {''.join(chr(b) if 32<=b<127 else '.' for b in chunk)}")
else:
    print("res.dat not found")
