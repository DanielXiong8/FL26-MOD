import sys, os
sys.path.insert(0, r"C:\FL26_Mod\scripts")
from decode_proto import decode_message, format_fields

for name in ["player.dat", "player2.dat"]:
    path = rf"C:\FL26_Mod\saves\exported_v2\files_root\{name}"
    if not os.path.exists(path):
        print(f"{name}: NOT FOUND")
        continue
    with open(path, "rb") as f:
        data = f.read()
    print(f"\n=== {name} ({len(data)}B) ===")
    print(f"first 64 hex: {data[:64].hex()}")
    
    # Try protobuf decode
    try:
        fields = decode_message(data, max_depth=4)
        lines = format_fields(fields)
        for line in lines[:80]:
            print(line)
        if len(lines) > 80:
            print(f"  ... ({len(lines)} total lines)")
    except Exception as e:
        print(f"protobuf decode failed: {e}")
