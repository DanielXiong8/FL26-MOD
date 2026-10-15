import sqlite3, sys, shutil
sys.path.insert(0, r'C:\FL26_Mod\tools\custom_player_editor')
from protobuf_editor import *
from sqlite_store import SaveDB

shutil.copy2(r'C:\FL26_Mod\saves\original\PlayerCareer\PlayerCareer20260831160348.db',
             r'C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db')

db = SaveDB(r'C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db')
p_raw = db.get_player(1)
fields = parse_fields(p_raw)
f9 = find_field(fields, 9)
name_f = find_field(f9.children, 1)

print(f'type(children): {type(name_f.children)}')
print(f'children value: {name_f.children}')
print(f'children is None: {name_f.children is None}')

set_string(name_f, 'ZZSaveTest')
print(f'\nafter set_string:')
print(f'type(children): {type(name_f.children)}')
print(f'children value: {name_f.children}')
print(f'children is None: {name_f.children is None}')
print(f'raw_bytes: {name_f.raw_bytes}')

# Manual serialize of just this field
field_bytes = name_f.serialize()
print(f'\nfield serialize: {field_bytes.hex()}')

# Full serialize
result = serialize_fields(fields)
target = b'ZZSaveTest'
bad = b'Z\x08SaveTest'
print(f'ZZSaveTest at: {result.find(target)}')
print(f'Z+x08 at: {result.find(bad)}')
db.close()
