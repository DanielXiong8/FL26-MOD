# -*- coding: utf-8 -*-
"""FL26 Archives protobuf editor — minimal, byte-preserving.

Payload format observations (Friendly/friendly.db):
  team_blob.payload: f1=team_id(varint), f2=repeated sub-message{f1=player_id, ...},
                     f3=packed varint roster list, f6/f13 misc
  player_blob.payload: f1=player_id, f2=state(1-4), f5=team_id, f10=ovr

Editor rule: parse to (field_no, wire_type, value) tuples preserving original order;
value = int for wt=0, bytes for wt=2. Re-serialize reproduces the exact original
bytes for unmodified payloads (self-test must pass before any write).
"""
import io, sqlite3, hashlib, json, os, shutil, time


def rv_dec(b, i):
    v = 0; sh = 0
    while True:
        x = b[i]; i += 1
        v |= (x & 0x7f) << sh; sh += 7
        if not (x & 0x80):
            return v, i


def rv_enc(v):
    out = bytearray()
    while True:
        b7 = v & 0x7f
        v >>= 7
        if v:
            out.append(b7 | 0x80)
        else:
            out.append(b7)
            return bytes(out)


def parse(b):
    fields = []
    i = 0
    n = len(b)
    while i < n:
        tag, i = rv_dec(b, i)
        fno, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = rv_dec(b, i)
            fields.append((fno, 0, v))
        elif wt == 2:
            ln, i = rv_dec(b, i)
            fields.append((fno, 2, b[i:i+ln]))
            i += ln
        elif wt == 5:
            fields.append((fno, 5, b[i:i+4])); i += 4
        elif wt == 1:
            fields.append((fno, 1, b[i:i+8])); i += 8
        else:
            raise ValueError('unsupported wire type %d at %d' % (wt, i))
    return fields


def serialize(fields):
    out = io.BytesIO()
    for fno, wt, v in fields:
        out.write(rv_enc((fno << 3) | wt))
        if wt == 0:
            out.write(rv_enc(v))
        elif wt == 2:
            out.write(rv_enc(len(v)))
            out.write(v)
        else:
            out.write(v)
    return out.getvalue()


def packed_varints(b):
    vals, i = [], 0
    while i < len(b):
        v, i = rv_dec(b, i)
        vals.append(v)
    return vals


def packed_enc(vals):
    return b''.join(rv_enc(v) for v in vals)


def self_test(payload):
    """serialize(parse(x)) == x — must hold before any edit is trusted."""
    return serialize(parse(payload)) == payload


def roster_of(team_payload):
    """Return {'fields','subs','roster'} for a team_blob payload."""
    fields = parse(team_payload)
    subs = [parse(v) for fno, wt, v in fields if fno == 2 and wt == 2]
    packed = None
    for fno, wt, v in fields:
        if fno == 3 and wt == 2:
            packed = packed_varints(v)
    return {'fields': fields, 'subs': subs, 'roster': packed or []}


def team_remove_player(team_payload, pid):
    """Remove one player from a team payload (sub-message + packed roster)."""
    fields = parse(team_payload)
    out_fields = []
    removed = 0
    for fno, wt, v in fields:
        if fno == 2 and wt == 2:
            sub = parse(v)
            if sub and sub[0][0] == 1 and sub[0][2] == pid:
                removed += 1
                continue
            out_fields.append((fno, wt, v))
        elif fno == 3 and wt == 2:
            vals = packed_varints(v)
            if pid in vals:
                vals.remove(pid)
                removed += 1
                v = packed_enc(vals)
            out_fields.append((fno, wt, v))
        else:
            out_fields.append((fno, wt, v))
    return serialize(out_fields), removed


def team_add_player(team_payload, pid, slot=0):
    """Append one player sub-message + packed roster entry to a team payload."""
    fields = parse(team_payload)
    out_fields = []
    for fno, wt, v in fields:
        if fno == 3 and wt == 2:
            vals = packed_varints(v)
            if pid not in vals:
                vals.append(pid)
                v = packed_enc(vals)
            out_fields.append((fno, wt, v))
        else:
            out_fields.append((fno, wt, v))
    sub = serialize([(1, 0, pid)])
    out_fields.append((2, 2, sub))
    return serialize(out_fields)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


class SaveRun:
    """One audited save roundtrip: runs/save/<run_id>/ with full provenance."""

    def __init__(self, runs_root, note=''):
        ts = time.strftime('%Y%m%d_%H%M%S')
        self.run_id = 'save_%s' % ts
        self.dir = os.path.join(runs_root, 'runs', 'save', self.run_id)
        os.makedirs(os.path.join(self.dir, 'exported'), exist_ok=True)
        os.makedirs(os.path.join(self.dir, 'modified'), exist_ok=True)
        self.manifest = {'run_id': self.run_id, 'created': ts, 'note': note,
                         'steps': [], 'sha256': {}, 'limitations': []}
        self.log_lines = []

    def log(self, msg):
        line = '[%s] %s' % (time.strftime('%H:%M:%S'), msg)
        self.log_lines.append(line)
        print(line)

    def step(self, name, ok, detail=''):
        self.manifest['steps'].append({'step': name, 'ok': bool(ok), 'detail': detail})
        self.log('STEP %-24s %s %s' % (name, 'OK' if ok else 'FAIL', detail))

    def record_sha(self, label, path):
        self.manifest['sha256'][label] = sha256_file(path)

    def snapshot_export(self, src_dir):
        dst = os.path.join(self.dir, 'exported')
        for root, _, files in os.walk(src_dir):
            rel = os.path.relpath(root, src_dir)
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(dst, rel, f))
        self.record_sha('exported_friendly_db', os.path.join(dst, 'Friendly', 'friendly.db'))
        self.log('exported snapshot -> %s' % dst)
        return dst

    def save_modified(self, rel_path, data_bytes):
        dst = os.path.join(self.dir, 'modified', rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(data_bytes)
        self.record_sha('modified_' + rel_path.replace('/', '_').replace('\\', '_'), dst)
        return dst

    def add_limitation(self, text):
        self.manifest['limitations'].append(text)

    def finalize(self, ok):
        self.manifest['final'] = 'PASS' if ok else 'FAIL'
        with open(os.path.join(self.dir, 'manifest.json'), 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=1, ensure_ascii=False)
        with open(os.path.join(self.dir, 'log.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_lines))
        self.log('run finalized: %s' % self.manifest['final'])
