# -*- coding: utf-8 -*-
"""
protobuf_editor.py — minimal protobuf wire-format reader/writer.
Preserves unknown fields. Only modifies known fields.
"""

def read_varint(data, pos):
    result = 0; shift = 0
    while True:
        b = data[pos]; result |= (b & 0x7F) << shift; pos += 1
        if not (b & 0x80): break
        shift += 7
    return result, pos

def write_varint(val):
    out = bytearray()
    while True:
        b = val & 0x7F; val >>= 7
        if val: out.append(b | 0x80)
        else: out.append(b); break
    return bytes(out)

class Field:
    def __init__(self, num, wire_type, value, raw_bytes=None, children=None):
        self.num = num
        self.wire_type = wire_type  # 0=varint, 1=fixed64, 2=length_delim, 5=fixed32
        self.value = value
        self.raw_bytes = raw_bytes  # for wire_type 2: the raw content bytes
        self.children = children    # for wire_type 2 parsed as message

    def serialize(self):
        tag = write_varint((self.num << 3) | self.wire_type)
        if self.wire_type == 0:
            return tag + write_varint(self.value)
        elif self.wire_type == 2:
            content = self.raw_bytes if self.children is None else serialize_fields(self.children)
            return tag + write_varint(len(content)) + content
        elif self.wire_type == 1:
            import struct
            return tag + struct.pack("<Q", self.value)
        elif self.wire_type == 5:
            import struct
            return tag + struct.pack("<I", self.value)
        else:
            raise ValueError(f"unknown wire_type {self.wire_type}")

def parse_fields(data):
    """Parse protobuf bytes into list of Field objects. Preserves all data."""
    fields = []
    pos = 0
    while pos < len(data):
        tag, pos = read_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            val, pos = read_varint(data, pos)
            fields.append(Field(field_num, 0, val))
        elif wire_type == 2:
            length, pos = read_varint(data, pos)
            raw = data[pos:pos+length]
            pos += length
            # Try to parse as nested message — but only accept if roundtrip is lossless
            children = None
            try:
                candidate = parse_fields(raw)
                if serialize_fields(candidate) == raw:
                    children = candidate
            except:
                pass
            fields.append(Field(field_num, 2, None, raw_bytes=raw, children=children))
        elif wire_type == 1:
            import struct
            val = struct.unpack_from("<Q", data, pos)[0]; pos += 8
            fields.append(Field(field_num, 1, val))
        elif wire_type == 5:
            import struct
            val = struct.unpack_from("<I", data, pos)[0]; pos += 4
            fields.append(Field(field_num, 5, val))
        else:
            raise ValueError(f"unknown wire_type {wire_type} at pos {pos}")
    return fields

def serialize_fields(fields):
    """Serialize list of Field objects back to bytes."""
    return b"".join(f.serialize() for f in fields)

def find_field(fields, num):
    """Find first field with given number."""
    for f in fields:
        if f.num == num:
            return f
    return None

def set_varint(fields, num, value):
    """Set a varint field. Creates if missing."""
    f = find_field(fields, num)
    if f and f.wire_type == 0:
        f.value = value
    else:
        fields.append(Field(num, 0, value))

def get_string(field):
    """Get string value from a length-delimited field."""
    if field and field.wire_type == 2:
        try:
            return field.raw_bytes.decode("utf-8")
        except:
            return None
    return None

def set_string(field, s):
    """Set string value on a length-delimited field. Clears children cache."""
    if field and field.wire_type == 2:
        field.raw_bytes = s.encode("utf-8")
        field.children = None
