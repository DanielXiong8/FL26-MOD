# -*- coding: utf-8 -*-
import sqlite3, os

def varint_at(buf, i):
    v, s = 0, 0
    while True:
        x = buf[i]; i += 1
        v |= (x & 0x7F) << s
        if not x & 0x80:
            return v, i
        s += 7

con = sqlite3.connect(os.path.join('save_user', 'Archives', 'SimpleClub', 'CompName_EnglishLeague.db'))
row = con.execute('SELECT payload FROM team_blob WHERE team_id=20027').fetchone()
b = row[0] if isinstance(row[0], bytes) else bytes(str(row[0]), 'utf-8', 'surrogateescape')
i = 0
while i < len(b):
    tag, i2 = varint_at(b, i)
    f, wt = tag >> 3, tag & 7
    if f == 3 and wt == 2:
        ln, i3 = varint_at(b, i2)
        print('F3LEN', ln)
        print(b[i3:i3 + ln].hex())
        break
    elif wt == 0:
        i = i2
    elif wt == 2:
        ln, i3 = varint_at(b, i2)
        i = i3 + ln
    else:
        break
