import sqlite3, sys, shutil
sys.path.insert(0, r'C:\FL26_Mod\tools\custom_player_editor')
from protobuf_editor import *
from sqlite_store import SaveDB

# Restore from original first
shutil.copy2(r'C:\FL26_Mod\saves\original\PlayerCareer\PlayerCareer20260831160348.db',
             r'C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db')

db = SaveDB(r'C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db')
p_raw = db.get_player(1)
print(f'original name area: {p_raw[14:34].hex()}')

fields = parse_fields(p_raw)
f9 = find_field(fields, 9)
name_f = find_field(f9.children, 1)
print(f'name_f children before: {name_f.children is None}')
set_string(name_f, 'ZZSaveTest')
print(f'name_f raw_bytes after set: {name_f.raw_bytes}')
print(f'name_f children after set: {name_f.children is None}')

new_payload = serialize_fields(fields)
print(f'new_payload name area: {new_payload[14:34].hex()}')
target = b'ZZSaveTest'
print(f'ZZSaveTest in new_payload: {new_payload.find(target)}')

# Write
db.set_player(1, new_payload)

# Read back
p2 = db.get_player(1)
print(f'readback name area: {p2[14:34].hex()}')
print(f'readback match: {p2 == new_payload}')
db.close()
