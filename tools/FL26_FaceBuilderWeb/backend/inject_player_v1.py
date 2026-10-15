# -*- coding: utf-8 -*-
"""inject_player_v1.py — cumulative player injector for the Web builder.

Device-proven Phase 13B formula, made CUMULATIVE (Phase 14A fix):
  - registry (player_registry.json) is the source of truth for all web-built players
  - EVERY build injects ALL registry players + the new one, so the device Archives
    roster never references dead pids (user-hit crash: jersey 30 dup -> China
    team unopenable)
  - pids/jerseys never reused (registry + base gamedata checked)
  - team roster cap 33 enforced BEFORE build (43 men = AFH dead match, device-proven)

Photo face limitation (shared texture slot): face_eastAsia_new1 is ONE slot for
all b1=14 players — the LATEST build's bake wins; earlier photo-faced players
revert to the latest face until V1.2 multi-slot (b1 10-15 mapping unverified).
"""
import io, os, shutil, struct, subprocess, zipfile, json, sys
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
HERE = os.path.dirname(__file__)
SRC_GAMEDATA = os.path.join(HERE, 'gamedata_orig.unity3d')
BASE_APK     = os.path.join(ROOT, 'build', 'base_debuggable2.apk')
BT = os.path.join(ROOT, 'android-sdk', 'build-tools', '36.0.0')
KEYSTORE = os.path.join(ROOT, r'build\fl26_test.keystore')
ROSTER_CAP = 33
sys.path.insert(0, HERE)


def parse_plyrcsv0(raw):
    off = 8
    ncnt, = struct.unpack_from('<H', raw, off); off += 2
    nations = []
    for _ in range(ncnt):
        ln, = struct.unpack_from('<H', raw, off); off += 2
        nations.append(raw[off:off+ln*2].decode('utf-16-le', errors='replace')); off += ln*2
    pcnt, = struct.unpack_from('<I', raw, off); off += 4
    recs = []
    for _ in range(pcnt):
        pid, = struct.unpack_from('<I', raw, off); off += 4
        ln, = struct.unpack_from('<H', raw, off); off += 2
        name = raw[off:off+ln*2].decode('utf-16-le', errors='replace'); off += ln*2
        fa, fb, fc, nat = struct.unpack_from('<HHHH', raw, off); off += 8
        b1, b16, b0 = raw[off], raw[off+1], raw[off+2]; off += 3
        attrs = list(raw[off:off+17]); off += 17
        tail16, = struct.unpack_from('<H', raw, off); off += 2
        tail8 = raw[off]; off += 1
        year, = struct.unpack_from('<I', raw, off); off += 4
        recs.append({'pid': pid, 'name': name, 'fa': fa, 'fb': fb, 'fc': fc, 'nat': nat,
                     'b1': b1, 'b16': b16, 'b0': b0, 'attrs': attrs,
                     'tail16': tail16, 'tail8': tail8, 'year': year})
    return nations, recs


def serialize_plyrcsv0(nations, recs):
    out = io.BytesIO()
    out.write(b'plyrcsv0')
    out.write(struct.pack('<H', len(nations)))
    for n in nations:
        nb = n.encode('utf-16-le', errors='replace')
        out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
    out.write(struct.pack('<I', len(recs)))
    for r in recs:
        out.write(struct.pack('<I', r['pid']))
        nb = r['name'].encode('utf-16-le', errors='replace')
        out.write(struct.pack('<H', len(nb)//2)); out.write(nb)
        out.write(struct.pack('<HHHH', r['fa'], r['fb'], r['fc'], r['nat']))
        out.write(bytes([r['b1'], r['b16'], r['b0']]))
        out.write(bytes(r['attrs']))
        out.write(struct.pack('<H', r['tail16']))
        out.write(bytes([r['tail8']]))
        out.write(struct.pack('<I', r['year']))
    return out.getvalue()


def log(msg):
    print('[inject] %s' % msg, flush=True)


def _ensure_src():
    global SRC_GAMEDATA
    if not os.path.exists(SRC_GAMEDATA):
        with zipfile.ZipFile(BASE_APK) as z:
            with open(SRC_GAMEDATA, 'wb') as f:
                f.write(z.read('assets/bundles/gamedata.unity3d'))
        log('extracted original gamedata from base APK')


def build_pa_record(ref_app, ex):
    app = bytearray(ref_app)
    app[0] = ex['skin_tone'] & 0xFF
    app[1] = ex['face_texture_id'] & 0xFF
    app[5] = ex['hair_color_id'] & 0xFF
    if ex.get('beard_enabled'):
        app[6] = max(1, min(22, int(ex['beard_style_id'])))
        app[7] = 0
    else:
        app[6] = 255
        app[7] = 127
    app[8] = max(1, min(7, int(ex['eyebrow_index'])))
    return bytes(app)


def build_pa_record_origin(ex):
    """ZERO-CLONE PA record: built from scratch, no reference player bytes.
    Byte semantics from Phase13B device probes:
      b0 skin tone, b1 face texture slot (14=eastAsia_new1 -> photo bake),
      b3/b4 hair index+flag (255/0 = game default hairstyle),
      b5 hair color, b6/b7 beard style+flag (255/127 = off), b8 eyebrow,
      b14 face-shape template (13-18 = EA range; 18 = neutral default).
    Everything else neutral (127 padding like game-omitted fields)."""
    app = bytearray(17)
    app[0] = ex['skin_tone'] & 0xFF
    app[1] = ex['face_texture_id'] & 0xFF
    app[3] = 255          # hair index: default
    app[4] = 0            # hair flag
    app[5] = ex['hair_color_id'] & 0xFF
    if ex.get('beard_enabled'):
        app[6] = max(1, min(22, int(ex['beard_style_id'])))
        app[7] = 0
    else:
        app[6] = 255
        app[7] = 127
    app[8] = max(1, min(7, int(ex['eyebrow_index'])))
    app[9] = 127          # unused padding (game default)
    app[14] = int(ex.get('b14', 18)) & 0xFF  # face-shape template row
    app[16] = 127
    return bytes(app)


def run(cfg, workdir):
    """cfg: appearance_state of the NEW player. Returns {apk, pid, sha256, roster}. """
    import hashlib
    import registry as reg
    _ensure_src()
    ident = cfg['player_identity']
    team = ident['team_id']
    jersey = int(ident['jersey_number'])
    ref_pid = int(cfg.get('reference_pid') or 0)
    out_apk = os.path.join(workdir, 'player.apk')

    # face texture slot auto-allocation: b1 10-15 -> face_eastAsia_new1-6
    # (device-probe mapping). 0 = auto: lowest slot not used by ANY player.
    ftid = int(cfg['explicit'].get('face_texture_id') or 0)
    if not ftid:
        used = {int(p['face_texture_id']) for p in reg.all_players() if p.get('face_texture_id')}
        free = [b for b in range(10, 16) if b not in used]
        if not free:
            raise ValueError('all 6 EA face slots (b1 10-15) are in use')
        ftid = free[0]
        cfg['explicit']['face_texture_id'] = ftid
        log('face slot auto-allocated: b1=%d -> face_eastAsia_new%d' % (ftid, ftid - 9))

    env = UnityPy.load(SRC_GAMEDATA)
    assets = {}
    for obj in env.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read(check_read=False)
            if d.m_Name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
                raw = d.m_Script
                assets[d.m_Name] = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)

    # ---- base state + registry ----
    cp0 = assets['ClubPlayer']
    n1_0, = struct.unpack_from('<I', cp0, 0)
    off = 4 + n1_0*8
    base_count, base_jerseys = 0, set()
    base_used = set()
    while off + 17 <= len(cp0):
        tid, p, f1, f2 = struct.unpack_from('<IIII', cp0, off)
        base_used.add(p)
        if tid == team:
            base_count += 1
            base_jerseys.add(f1)
        off += 17
    prior = reg.by_team(team)
    new_count = base_count + len(prior) + 1
    if new_count > ROSTER_CAP:
        raise ValueError('This team has reached the supported roster limit (%d/%d after adding).' % (new_count - 1, ROSTER_CAP))
    taken = base_jerseys | reg.jerseys_in_team(team)
    if jersey in taken:
        raise ValueError('Jersey number %d already taken in this team.' % jersey)
    log('team %d: base %d + prior %d + new 1 = %d/%d | jersey %d free' % (
        team, base_count, len(prior), new_count, ROSTER_CAP, jersey))

    # ---- Players: ORIGIN (zero-clone) or reference-clone ----
    origin = (cfg.get('mode') == 'origin')
    nations, recs = parse_plyrcsv0(assets['Players'])
    if origin:
        tmpl = None
    else:
        ref_pid = int(cfg['reference_pid'])
        tmpl = next(r for r in recs if r['pid'] == ref_pid)
    pid = 175924
    while pid in base_used or pid in reg.used_pids():
        pid += 1
    new_players = []   # (pid, name, nat, attrs, jersey, pa_app_bytes, is_new)
    for p in prior:
        new_players.append({'pid': p['pid'], 'name': p['name'],
                            'nat': p.get('nat', tmpl['nat'] if tmpl else 24),
                            'attrs': p.get('attrs'), 'jersey': p['jersey'],
                            'ftid': p.get('face_texture_id'),
                            'b14': p.get('b14'), 'fa': p.get('fa'),
                            'fb': p.get('fb'), 'fc': p.get('fc'),
                            'app': None, 'prev': True})
    new_players.append({'pid': pid, 'name': ident['name'], 'nat': ident['nationality_nat'],
                        'attrs': list(ident['attrs_17']), 'jersey': jersey,
                        'ftid': cfg['explicit']['face_texture_id'],
                        'app': None, 'prev': False})
    log('players this APK: %d (prior %d + new %d @ pid %d) mode=%s' % (
        len(new_players), len(prior), 1, pid, cfg.get('mode')))

    # ---- SLOT EXCLUSIVITY: no other player may wear our custom face slot ----
    # (device evidence 2026-09-11: original players whose material binds the
    # same EA texture slot wore our bake - Wan S. got MyFace's nose). Reassign
    # every OTHER player whose b1 == our slot to a rotation of the remaining
    # EA slots; the 6 stock EA textures are all generic same-ethnicity faces,
    # so the visual change for reassigned originals is minimal.
    my_slot = int(cfg['explicit']['face_texture_id'])
    custom_pids = set()
    try:
        import registry as _reg
        custom_pids = {int(p['pid']) for p in _reg.all_players() if p.get('face_texture_id')}
    except Exception:
        pass
    alt_slots = [b for b in range(10, 16) if b != my_slot]
    pa_raw = assets['PlayerAppearanceTable']
    n_pa, = struct.unpack_from('<I', pa_raw, 0)
    pa_idx = [struct.unpack_from('<II', pa_raw, 4 + i*8) for i in range(n_pa)]
    pa_buf = bytearray(pa_raw)
    reassigned = 0
    rot = 0
    for pa_pid, off in pa_idx:
        if pa_pid in custom_pids:
            continue
        app1 = pa_buf[off + 5]
        if app1 == my_slot:
            pa_buf[off + 5] = alt_slots[rot % len(alt_slots)]
            rot += 1
            reassigned += 1
    assets['PlayerAppearanceTable'] = bytes(pa_buf)
    n_reassigned_players = reassigned
    for r in recs:
        if r['pid'] in custom_pids:
            continue
        if r['b1'] == my_slot:
            r['b1'] = alt_slots[rot % len(alt_slots)]
            rot += 1
            reassigned += 1
    log('slot exclusivity: my slot b1=%d, reassigned %d rows/players to %s' % (
        my_slot, reassigned, alt_slots))

    pa = assets['PlayerAppearanceTable']
    n, = struct.unpack_from('<I', pa, 0)
    idx = [struct.unpack_from('<II', pa, 4 + i*8) for i in range(n)]
    idx_map = dict(idx)
    data = pa[4 + n*8:]
    if origin:
        ref_app = None
    else:
        t_off = idx_map[ref_pid]
        ref_app = bytes(pa[t_off+4:t_off+21])

    new_recs = []
    pa_recs = []
    for pinfo in new_players:
        if pinfo['prev']:
            # prior player: keep stored appearance from registry (b bytes snapshot)
            app = bytes(pinfo.get('app') or (ref_app or build_pa_record_origin(cfg['explicit'])))
        elif origin:
            app = build_pa_record_origin(cfg['explicit'])
        else:
            app = build_pa_record(ref_app, cfg['explicit'])
        if pinfo.get('ftid'):
            app = bytes(app[:1]) + bytes([int(pinfo['ftid']) & 0xFF]) + app[2:]
        if pinfo.get('b14') is not None:
            app = bytes(app[:14]) + bytes([int(pinfo['b14']) & 0xFF]) + app[15:]
        pinfo['app'] = app
        pa_recs.append(struct.pack('<I', pinfo['pid']) + app)
        if origin:
            # ZERO-CLONE player record: every field written explicitly.
            # name/nat/attrs from user input; head-model triple fa/fb/fc = 0
            # (device-proven: all-zero renders the DEFAULT head model); b1=14
            # routes the face texture to our photo bake; no template player read.
            r = {'pid': pinfo['pid'], 'name': pinfo['name'],
                 'fa': int(pinfo.get('fa') or 0), 'fb': int(pinfo.get('fb') or 0),
                 'fc': int(pinfo.get('fc') or 0), 'nat': pinfo['nat'],
                 'b1': int(pinfo.get('ftid') or cfg['explicit']['face_texture_id']) & 0xFF,
                 'b16': 0, 'b0': cfg['explicit']['skin_tone'] & 0xFF,
                 'attrs': list(pinfo['attrs'] or ident['attrs_17']),
                 'tail16': 0, 'tail8': 0, 'year': 2026}
        else:
            r = dict(tmpl)
            r['pid'] = pinfo['pid']
            r['name'] = pinfo['name']
            r['nat'] = pinfo['nat']
            if pinfo['attrs']:
                r['attrs'] = pinfo['attrs']
        new_recs.append(r)
    k = len(new_players)
    new_n = n + k
    base_off = 4 + new_n*8 + len(data)
    players_raw = serialize_plyrcsv0(nations, recs + new_recs)

    out2 = io.BytesIO()
    out2.write(struct.pack('<I', new_n))
    for kk, oo in idx:
        out2.write(struct.pack('<II', kk, oo + 8*k))
    for j, pr in enumerate(pa_recs):
        out2.write(struct.pack('<II', new_players[j]['pid'], base_off + j*21))
    out2.write(data)
    for pr in pa_recs:
        out2.write(pr)
    pa_raw = out2.getvalue()
    log('PA: %d -> %d (+%d)' % (n, new_n, k))

    # ---- ClubPlayer ----
    cp = assets['ClubPlayer']
    n1, = struct.unpack_from('<I', cp, 0)
    sec1 = [list(struct.unpack_from('<II', cp, 4 + i*8)) for i in range(n1)]
    sec2 = []
    off = 4 + n1*8
    while off + 17 <= len(cp):
        tid, p, f1, f2 = struct.unpack_from('<IIII', cp, off)
        sec2.append({'team_id': tid, 'player_id': p, 'f1': f1, 'f2': f2, 'f3': cp[off+16]})
        off += 17
    for e in sec1:
        if e[0] == team:
            e[1] += k
    for pinfo in new_players:
        sec2.append({'team_id': team, 'player_id': pinfo['pid'],
                     'f1': pinfo['jersey'], 'f2': 6912, 'f3': 0})
    out = io.BytesIO()
    out.write(struct.pack('<I', len(sec1)))
    for tid, cnt in sec1:
        out.write(struct.pack('<II', tid, cnt))
    for r in sec2:
        out.write(struct.pack('<IIII', r['team_id'], r['player_id'], r['f1'], r['f2']))
        out.write(bytes([r['f3']]))
    clubplayer_raw = out.getvalue()

    # ---- rebuild bundle ----
    dst_gamedata = os.path.join(workdir, 'gamedata.unity3d')
    shutil.copyfile(SRC_GAMEDATA, dst_gamedata)
    env2 = UnityPy.load(dst_gamedata)
    payloads = {'Players': players_raw, 'ClubPlayer': clubplayer_raw, 'PlayerAppearanceTable': pa_raw}
    mod = 0
    for obj in env2.objects:
        if obj.type.name == 'TextAsset':
            d = obj.read(check_read=False)
            if d.m_Name in payloads:
                d.m_Script = payloads[d.m_Name].decode('utf-8', errors='surrogateescape')
                d.save(); mod += 1
    with open(dst_gamedata, 'wb') as f:
        f.write(env2.file.save())
    log('gamedata rebuilt, TextAssets modified: %d' % mod)

    # ---- APK ----
    with zipfile.ZipFile(BASE_APK, 'r') as zin, zipfile.ZipFile(out_apk + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/gamedata.unity3d':
                with open(dst_gamedata, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
    shutil.move(out_apk + '.tmp', out_apk)

    envv = dict(os.environ)
    JH = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
    envv['JAVA_HOME'] = JH; envv['Path'] = JH + r'\bin;' + envv.get('Path', '')
    aligned = out_apk.replace('.apk', '_aligned.apk')
    subprocess.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', out_apk, aligned],
                   capture_output=True, env=envv)
    if os.path.exists(aligned):
        os.replace(aligned, out_apk)
    r = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks', KEYSTORE,
                        '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', out_apk],
                       capture_output=True, text=True, env=envv)
    if r.returncode != 0:
        raise ValueError('apksigner: %s' % r.stderr[-300:])
    v = subprocess.run([os.path.join(BT, 'apksigner.bat'), 'verify', out_apk],
                       capture_output=True, text=True, env=envv)
    if v.returncode != 0:
        raise ValueError('verify failed: %s' % v.stdout[-200:])
    log('sign+verify OK')
    h = hashlib.sha256()
    with open(out_apk, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return {'apk': out_apk, 'pid': pid, 'team': team, 'jersey': jersey,
            'sha256': h.hexdigest(), 'size': os.path.getsize(out_apk),
            'roster': new_count}


if __name__ == '__main__':
    cfgp = os.environ.get('FL26_PLAYER_CONFIG')
    wd = sys.argv[1] if len(sys.argv) > 1 else '.'
    cfg = json.load(open(cfgp, encoding='utf-8'))
    print(json.dumps(run(cfg, wd), indent=1))
