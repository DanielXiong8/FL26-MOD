# Custom Player Editor

FL26 Mod save editor for UserPlayer (Player Career mode).

## Files

- `editor.py` — CLI entry point
- `protobuf_editor.py` — wire-format protobuf reader/writer (preserves unknown fields)
- `sqlite_store.py` — SQLite access layer

## Usage

```bash
python editor.py inspect <db_path>          # show UserPlayer + attributes
python editor.py set-name <db> "Name"       # change player name
python editor.py set-kitname <db> "KIT"     # change jersey name
python editor.py set-kitnumber <db> 7       # change jersey number
python editor.py set-attribute <db> balance 99
python editor.py set-appearance <db> 240
python editor.py export <db> out.json       # export to JSON
python editor.py backup <db>                # create backup
```

## Architecture

- `player_blob` (SQLite): 37,616 players. Outer protobuf: f1=pid, f4=pos, f5=team, f8=jersey, f9=details.
  - f9 nested: f1=name, f2=birth, f3=height, f4-f20=17 attributes, f21=overall, f22=foot
- `archive_blob` (SQLite): career metadata. f2=UserPlayer meta (kit name, number, appearance, position), f8=season state.
