import sqlite3
db = sqlite3.connect(r'C:\FL26_Mod\saves\working\PlayerCareer\PlayerCareer20260831160348.db')
cur = db.cursor()
cur.execute('SELECT payload FROM player_blob WHERE player_id=1')
raw = cur.fetchone()[0]
print(f'len: {len(raw)}')
print(f'hex: {raw.hex()}')
idx1 = raw.find(b'ZZSaveTest')
idx2 = raw.find(b'Z\x08SaveTest')
print(f'ZZSaveTest at: {idx1}')
print(f'Z+x08 at: {idx2}')
print(f'name area: {raw[14:34].hex()}')
db.close()
