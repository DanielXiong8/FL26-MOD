# -*- coding: utf-8 -*-
import sqlite3, os

con = sqlite3.connect(os.path.join('save_user', 'Archives', 'SimpleClub', 'CompName_EnglishLeague.db'))
row = con.execute('SELECT payload FROM team_blob WHERE team_id=20027').fetchone()
b = row[0] if isinstance(row[0], bytes) else bytes(str(row[0]), 'utf-8', 'surrogateescape')
print('LEN', len(b))
print(b.hex())
# also same team from our fresh-aligned save for comparison
con2 = sqlite3.connect(os.path.join('save_v16', 'Archives', 'SimpleClub', 'CompName_EnglishLeague.db'))
row2 = con2.execute('SELECT payload FROM team_blob WHERE team_id=20027').fetchone()
if row2:
    b2 = row2[0] if isinstance(row2[0], bytes) else bytes(str(row2[0]), 'utf-8', 'surrogateescape')
    print('FRESH LEN', len(b2))
    print(b2.hex())
