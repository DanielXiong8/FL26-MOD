# -*- coding: utf-8 -*-
"""decode_proto.py — generic protobuf wire-format decoder (no schema needed).
Dumps field numbers, wire types, values. Handles nested messages."""
import struct, sys, os

def read_varint(data, pos):
    result = 0
    shift = 0
    while True:
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, pos

def decode_message(data, depth=0, max_depth=5):
    """Decode protobuf wire format. Returns list of (field, wire_type, value, raw_bytes)."""
    fields = []
    pos = 0
    while pos < len(data):
        try:
            tag, pos = read_varint(data, pos)
            field_num = tag >> 3
            wire_type = tag & 0x07
            
            if wire_type == 0:  # varint
                val, pos = read_varint(data, pos)
                fields.append((field_num, "varint", val, None))
            elif wire_type == 1:  # 64-bit
                val = struct.unpack_from("<d", data, pos)[0]
                fields.append((field_num, "fixed64", val, data[pos:pos+8]))
                pos += 8
            elif wire_type == 2:  # length-delimited
                length, pos = read_varint(data, pos)
                raw = data[pos:pos+length]
                pos += length
                # Try to decode as string
                try:
                    s = raw.decode("utf-8")
                    if all(32 <= ord(c) < 127 or ord(c) > 127 for c in s):
                        fields.append((field_num, "string", s, raw))
                        continue
                except:
                    pass
                # Try nested message
                if depth < max_depth and length > 0:
                    try:
                        nested = decode_message(raw, depth+1, max_depth)
                        if nested and all(f[0] > 0 for f in nested):
                            fields.append((field_num, "message", nested, raw))
                            continue
                    except:
                        pass
                fields.append((field_num, "bytes", f"{length}B", raw))
            elif wire_type == 5:  # 32-bit
                val = struct.unpack_from("<f", data, pos)[0]
                fields.append((field_num, "fixed32", val, data[pos:pos+4]))
                pos += 4
            else:
                fields.append((field_num, f"unknown_wire_{wire_type}", None, None))
                break
        except (IndexError, struct.error):
            break
    return fields

def format_fields(fields, indent=0):
    lines = []
    prefix = "  " * indent
    for f in fields:
        field_num, wtype, val, raw = f
        if wtype == "message":
            lines.append(f"{prefix}f{field_num} (message, {len(raw)}B):")
            lines.extend(format_fields(val, indent+1))
        elif wtype == "bytes":
            hex_preview = raw[:32].hex() if raw else ""
            lines.append(f"{prefix}f{field_num} (bytes[{val}]): {hex_preview}{'...' if raw and len(raw)>32 else ''}")
        elif wtype == "string":
            lines.append(f"{prefix}f{field_num} (string): {val!r}")
        elif wtype == "varint":
            lines.append(f"{prefix}f{field_num} (varint): {val}")
        elif wtype == "fixed32":
            lines.append(f"{prefix}f{field_num} (fixed32): {val}")
        elif wtype == "fixed64":
            lines.append(f"{prefix}f{field_num} (fixed64): {val}")
        else:
            lines.append(f"{prefix}f{field_num} ({wtype})")
    return lines

def main():
    path = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    with open(path, "rb") as f:
        data = f.read()
    print(f"File: {path} ({len(data)}B)")
    fields = decode_message(data, max_depth=max_depth)
    for line in format_fields(fields):
        print(line)

if __name__ == "__main__":
    main()
