import json, sys

with open(r'C:\FL26_Mod\recon\02_engine\il2cpp\out\script.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Search for CalculateImageSavePath
results = []
def search(obj, path=""):
    if isinstance(obj, dict):
        if 'Name' in obj and 'CalculateImageSavePath' in str(obj.get('Name', '')):
            results.append((path, obj))
        if 'name' in obj and 'CalculateImageSavePath' in str(obj.get('name', '')):
            results.append((path, obj))
        for k, v in obj.items():
            search(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            search(item, f"{path}[{i}]")

# Search top level
if isinstance(data, dict):
    for k, v in data.items():
        search(v, k)
elif isinstance(data, list):
    for i, item in enumerate(data):
        search(item, f"[{i}]")

print(f"Found {len(results)} matches")
for path, obj in results:
    print(f"\n=== {path} ===")
    if isinstance(obj, dict):
        for k, v in obj.items():
            sv = str(v)
            if len(sv) > 200:
                sv = sv[:200] + "..."
            print(f"  {k}: {sv}")
