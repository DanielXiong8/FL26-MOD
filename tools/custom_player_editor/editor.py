# -*- coding: utf-8 -*-
"""
editor.py — FL26 Custom Player Save Editor CLI.
Usage:
  python editor.py list <db>
  python editor.py inspect <db>
  python editor.py set-name <db> <name>
  python editor.py set-kitname <db> <kitname>
  python editor.py set-kitnumber <db> <number>
  python editor.py set-attribute <db> <attr> <value>
  python editor.py set-appearance <db> <id>
  python editor.py export <db> <out.json>
  python editor.py import <db> <in.json>
  python editor.py backup <db>
  python editor.py restore <db> <backup>
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from protobuf_editor import *
from sqlite_store import SaveDB

ATTR_NAMES = [
    "balance", "reaction", "acceleration", "velocity", "stamina",
    "agility", "shotpower", "standingtackle", "slidingtackle", "ballcontrol",
    "dribble", "shortpass", "highpass", "shot", "volley",
    "mental_defensivepositioning", "mental_vision"
]
# f9 sub-fields 4-20 = 17 attributes
ATTR_FIELD_BASE = 4  # f9.f4 = first attribute (balance)

def decode_player(payload):
    """Decode player_blob payload into structured dict."""
    fields = parse_fields(payload)
    result = {"_raw_fields": fields}

    f1 = find_field(fields, 1)
    result["player_id"] = f1.value if f1 else None

    f4 = find_field(fields, 4)
    result["position"] = f4.value if f4 else None

    f5 = find_field(fields, 5)
    result["team_id"] = f5.value if f5 else None

    f8 = find_field(fields, 8)
    result["jersey"] = f8.value if f8 else None

    f9 = find_field(fields, 9)
    if f9 and f9.children:
        detail = f9.children
        name_f = find_field(detail, 1)
        result["name"] = get_string(name_f) if name_f else None

        birth_f = find_field(detail, 2)
        result["birth_year"] = birth_f.value if birth_f else None

        height_f = find_field(detail, 3)
        result["height"] = height_f.value if height_f else None

        # 17 attributes
        attrs = {}
        for i, attr_name in enumerate(ATTR_NAMES):
            af = find_field(detail, ATTR_FIELD_BASE + i)
            if af:
                attrs[attr_name] = af.value
        result["attributes"] = attrs

        overall_f = find_field(detail, 21)
        result["overall"] = overall_f.value if overall_f else None

        foot_f = find_field(detail, 22)
        result["foot"] = foot_f.value if foot_f else None

    f11 = find_field(fields, 11)
    if f11 and f11.children:
        result["appearance"] = {f"f{f.num}": f.value for f in f11.children if f.wire_type == 0}

    return result

def encode_player(fields):
    """Encode player fields back to protobuf bytes, preserving unknown fields."""
    return serialize_fields(fields)

def decode_archive(payload):
    """Decode archive_blob payload."""
    fields = parse_fields(payload)
    result = {"_raw_fields": fields}

    # f2 = UserPlayer metadata
    f2 = find_field(fields, 2)
    if f2 and f2.children:
        up = f2.children
        kit_f = find_field(up, 3)
        result["user_kit_name"] = get_string(kit_f) if kit_f else None
        kitnum_f = find_field(up, 2)
        result["user_kit_number"] = kitnum_f.value if kitnum_f else None
        apid_f = find_field(up, 4)
        result["user_appearance_id"] = apid_f.value if apid_f else None
        pos_f = find_field(up, 5)
        result["user_position"] = pos_f.value if pos_f else None

    # f8.f22 = user's team_id
    f8 = find_field(fields, 8)
    if f8 and f8.children:
        for sub in f8.children:
            if sub.num == 1 and sub.children:
                for sf in sub.children:
                    if sf.num == 22:
                        result["user_team_id"] = sf.value

    return result

def cmd_inspect(db_path):
    db = SaveDB(db_path)
    # UserPlayer metadata from archive
    arch_raw = db.get_archive()
    arch = decode_archive(arch_raw)
    print("=== User Player (archive_blob) ===")
    print(f"  Kit Name:    {arch.get('user_kit_name')}")
    print(f"  Kit Number:  {arch.get('user_kit_number')}")
    print(f"  Appearance:  {arch.get('user_appearance_id')}")
    print(f"  Position:    {arch.get('user_position')}")
    print(f"  Team ID:     {arch.get('user_team_id')}")

    # Player data from player_blob
    print(f"\n=== Player Data (player_blob, id=1) ===")
    p_raw = db.get_player(1)
    if p_raw:
        p = decode_player(p_raw)
        print(f"  Name:        {p.get('name')}")
        print(f"  Position:    {p.get('position')}")
        print(f"  Team ID:     {p.get('team_id')}")
        print(f"  Jersey:      {p.get('jersey')}")
        print(f"  Birth Year:  {p.get('birth_year')}")
        print(f"  Height:      {p.get('height')}")
        print(f"  Overall:     {p.get('overall')}")
        print(f"  Foot:        {p.get('foot')}")
        print(f"\n  === 17 Attributes ===")
        for attr in ATTR_NAMES:
            val = p.get("attributes", {}).get(attr, "?")
            print(f"    {attr:32s}: {val}")
        if "appearance" in p:
            print(f"\n  Appearance IDs: {p['appearance']}")
    db.close()

def cmd_set_name(db_path, name):
    db = SaveDB(db_path)
    p_raw = db.get_player(1)
    fields = parse_fields(p_raw)
    f9 = find_field(fields, 9)
    if f9 and f9.children:
        name_f = find_field(f9.children, 1)
        if name_f:
            old_name = get_string(name_f)
            set_string(name_f, name)
            new_payload = encode_player(fields)
            db.set_player(1, new_payload)
            print(f"Name: {old_name!r} -> {name!r}")
            print(f"Payload: {len(p_raw)}B -> {len(new_payload)}B")
        else:
            print("ERROR: name field not found")
    db.close()

def cmd_set_attribute(db_path, attr_name, value):
    if attr_name not in ATTR_NAMES:
        print(f"ERROR: unknown attribute {attr_name!r}. Valid: {ATTR_NAMES}")
        return
    value = int(value)
    if not (0 <= value <= 127):
        print(f"ERROR: value must be 0-127")
        return
    db = SaveDB(db_path)
    p_raw = db.get_player(1)
    fields = parse_fields(p_raw)
    f9 = find_field(fields, 9)
    if f9 and f9.children:
        idx = ATTR_NAMES.index(attr_name)
        field_num = ATTR_FIELD_BASE + idx
        af = find_field(f9.children, field_num)
        if af:
            old_val = af.value
            af.value = value
            new_payload = encode_player(fields)
            db.set_player(1, new_payload)
            print(f"{attr_name}: {old_val} -> {value}")
        else:
            print(f"ERROR: attribute field {field_num} not found")
    db.close()

def cmd_set_kitname(db_path, kitname):
    db = SaveDB(db_path)
    arch_raw = db.get_archive()
    fields = parse_fields(arch_raw)
    f2 = find_field(fields, 2)
    if f2 and f2.children:
        kit_f = find_field(f2.children, 3)
        if kit_f:
            old = get_string(kit_f)
            set_string(kit_f, kitname)
            new_payload = serialize_fields(fields)
            db.set_archive(new_payload)
            print(f"Kit name: {old!r} -> {kitname!r}")
        else:
            print("ERROR: kit name field not found")
    db.close()

def cmd_set_kitnumber(db_path, number):
    db = SaveDB(db_path)
    arch_raw = db.get_archive()
    fields = parse_fields(arch_raw)
    f2 = find_field(fields, 2)
    if f2 and f2.children:
        num_f = find_field(f2.children, 2)
        if num_f:
            old = num_f.value
            num_f.value = int(number)
            new_payload = serialize_fields(fields)
            db.set_archive(new_payload)
            print(f"Kit number: {old} -> {number}")
        else:
            print("ERROR: kit number field not found")
    db.close()

def cmd_set_appearance(db_path, apid):
    db = SaveDB(db_path)
    arch_raw = db.get_archive()
    fields = parse_fields(arch_raw)
    f2 = find_field(fields, 2)
    if f2 and f2.children:
        ap_f = find_field(f2.children, 4)
        if ap_f:
            old = ap_f.value
            ap_f.value = int(apid)
            new_payload = serialize_fields(fields)
            db.set_archive(new_payload)
            print(f"Appearance ID: {old} -> {apid}")
        else:
            print("ERROR: appearance field not found")
    db.close()

def cmd_export(db_path, out_path):
    db = SaveDB(db_path)
    arch = decode_archive(db.get_archive())
    player = decode_player(db.get_player(1))
    # Remove internal fields
    arch.pop("_raw_fields", None)
    player.pop("_raw_fields", None)
    data = {"user_player_meta": arch, "player_data": player}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"-> {out_path}")
    db.close()

def cmd_backup(db_path):
    db = SaveDB(db_path)
    bdir = os.path.join(os.path.dirname(os.path.abspath(db_path)), "..", "backups")
    dst, sha = db.backup(bdir)
    print(f"Backup: {dst}")
    print(f"SHA256: {sha}")
    db.close()

def cmd_list(db_path):
    db = SaveDB(db_path)
    count = db.player_count()
    print(f"Total players: {count}")
    rows = db.list_players(20)
    for r in rows:
        print(f"  pid={r[0]:<8} payload={r[1]}B")
    db.close()

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    cmd = sys.argv[1]
    db_path = sys.argv[2]

    if cmd == "list": cmd_list(db_path)
    elif cmd == "inspect": cmd_inspect(db_path)
    elif cmd == "set-name": cmd_set_name(db_path, sys.argv[3])
    elif cmd == "set-kitname": cmd_set_kitname(db_path, sys.argv[3])
    elif cmd == "set-kitnumber": cmd_set_kitnumber(db_path, sys.argv[3])
    elif cmd == "set-attribute": cmd_set_attribute(db_path, sys.argv[3], sys.argv[4])
    elif cmd == "set-appearance": cmd_set_appearance(db_path, sys.argv[3])
    elif cmd == "export": cmd_export(db_path, sys.argv[3])
    elif cmd == "backup": cmd_backup(db_path)
    else: print(__doc__)

if __name__ == "__main__":
    main()
