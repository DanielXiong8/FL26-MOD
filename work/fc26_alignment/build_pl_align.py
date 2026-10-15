# -*- coding: utf-8 -*-
"""build_pl_align.py - THE 3-STEP ALIGNER ENGINE (user's workflow):
  step 1 真名   : rename Players.name by pid (pl_plan RENAME, pid-scoped = safe)
  step 2 分配   : TRANSFER (move existing pid to club) / INJECT (new pid) /
                  REMOVE (leaver membership), + verified OVR corrections (byte[1])
  step 3 队名   : Teams/strings already carry correct English names (Real_*), no-op
                  for this pass (verified: Real_EnglishA_Chelsea = "Chelsea").
Input : build/db_survey_gamedata.unity3d (CLEAN base - no prior injections)
Output: build/gamedata_pl2.unity3d + verification re-parse
"""
import io, json, os, struct, shutil
import UnityPy

BASE = r'D:\FL26_Mod\work\fc26_alignment'
SRC_GD = r'D:\FL26_Mod\build\db_survey_gamedata.unity3d'
OUT_GD = os.environ.get('ALIGN_OUT', r'D:\FL26_Mod\build\gamedata_pl2.unity3d')

PLAN_FILE = os.environ.get('ALIGN_PLAN', BASE + r'\pl_plan.json')
plan = json.load(open(PLAN_FILE, encoding='utf-8'))
MODE = os.environ.get('ALIGN_MODE', 'full')
if MODE != 'full':
    keep = set(MODE.split(','))
    for k in ('TRANSFER', 'INJECT', 'REMOVE', 'ATTACH'):
        if k not in keep:
            plan[k] = []
man = json.load(open(BASE + r'\pl_update_manifest.json', encoding='utf-8'))
sq = json.load(open(BASE + r'\squad_pl_full.json', encoding='utf-8'))

PL = {
 'Arsenal':20030,'Liverpool':20027,'Chelsea':20028,'Tottenham':20029,'Newcastle':20037,
 'ManCity':20026,'ManUnited':20031,'Bournemouth':20046,'AstonVilla':20039,'Brentford':20036,
 'Brighton':20035,'CrystalPalace':20038,'Everton':20041,'Fulham':20367,'Coventry':20324,
 'Ipswich':20398,'HullCity':20313,'NottinghamForest':20050,'Sunderland':20311,'WestHam':20032
}
NUM = {}
for club in PL:
    for pos in ('GK', 'DF', 'MF', 'FW'):
        for num, nm in sq.get(club, {}).get(pos, []) or []:
            if str(num).isdigit() and int(num) > 0:
                NUM[nm] = int(num)

DQD = {}
if os.path.exists(BASE + r'\dqd_abilities.json'):
    DQD = json.load(open(BASE + r'\dqd_abilities.json', encoding='utf-8'))
print('DQD abilities loaded: %d' % len(DQD))

NAT_OVERRIDE = {'Vitezslav Jaros': 'Czech Republic', 'Harvey Davies': 'England',
 'Jeremy Jacquet': 'France', 'Kostas Tsimikas': 'Greece', 'Ronald Araujo': 'Uruguay',
 'Luke Chambers': 'England', 'James McConnell': 'England', 'Victor Munoz': 'Spain',
 'Bradley Barcola': 'France', 'Lewis Koumas': 'Wales', 'Jayden Danns': 'England',
 'Mike Penders': 'Belgium', 'Teddy Sharman-Lowe': 'England', 'Marco Palestra': 'Italy',
 'Valentin Barco': 'Argentina', 'Maxence Lacroix': 'France', 'Geovany Quenda': 'Portugal',
 'Estêvão': 'Brazil', 'David Raya': 'Spain', 'Tommy Setford': 'England',
 'Zion Suzuki': 'Japan', 'Alejandro Garnacho': 'Argentina', 'António Silva': 'Portugal',
 'Julián Araujo': 'Mexico', 'Edson Álvarez': 'Mexico', 'Joël Veltman': 'Netherlands',
 'Ousmane Diomande': 'Ivory Coast', 'Daniel Muñoz': 'Colombia', 'Ibrahim Sangaré': 'Ivory Coast',
 'Ismaïla Sarr': 'Senegal', 'Cheick Doucouré': 'Mali', 'Daichi Kamada': 'Japan',
 'Takehiro Tomiyasu': 'Japan', 'Óscar Mingueza': 'Spain', 'Darío Osorio': 'Chile',
 'Jørgen Strand Larsen': 'Norway', 'Yéremy Pino': 'Spain', 'Dwight McNeil': 'England',
 'Hugo Larsson': 'Sweden', 'Sander Berge': 'Norway', 'Antonee Robinson': 'United States',
 'Bernd Leno': 'Germany', 'Joachim Andersen': 'Denmark', 'Manuel Ángel': 'Spain',
 'César Palacios': 'Spain', 'Gonzalo García': 'Spain', 'Ryan Sessegnon': 'England',
 'Emile Smith Rowe': 'England', 'Alex Iwobi': 'Nigeria', 'Alex Borto': 'United States',
 'Mamadou Sangaré': 'Mali', 'Kim Ji-Soo': 'Korea Republic', 'Kevin Schade': 'Germany',
 'Pascal Struijk': 'Netherlands', 'Bart Verbruggen': 'Netherlands', 'Pascal Groß': 'Germany',
 'Kaoru Mitoma': 'Japan', 'Ferdi Kadıoğlu': 'Turkey', 'Lewis Dunk': 'England',
 'Joël Piroe': 'Netherlands', 'Manor Solomon': 'Israel', 'Maxwel Cornet': 'Ivory Coast',
 'Arne Engels': 'Belgium', 'Taty Castellanos': 'Argentina', 'Jarrod Bowen': 'England',
 'Mads Hermansen': 'Denmark', 'Alphonse Areola': 'France', 'Morato': 'Brazil',
 'Konstantinos Mavropanos': 'Greece', 'Tomáš Souček': 'Czech Republic',
 'Maximilian Kilman': 'England', 'Adama Boiro': 'Spain',
 'Tommy Setford': 'England', 'Christos Tzolis': 'Greece', 'Lukáš Horníček': 'Czech Republic',
 'Ewen Jaouen': 'England', 'Aidan Harris': 'England', 'Bazoumana Touré': 'Ivory Coast',
 'Gerónimo Rulli': 'Argentina', 'Iliman Ndiaye': 'Senegal', 'Allan': 'Brazil',
 'Karl Darlow': 'England', 'Tyler Fletcher': 'Scotland', 'Max Aarons': 'England',
 'Daniel Jebbison': 'Canada', 'Álvaro Rodríguez': 'Spain', 'James Wright': 'England',
 'Benjamin Fredrick': 'Nigeria', 'Hadjam': 'Algeria', 'Chema Andrés': 'Spain',
 'Honest Ahanor': 'Italy', 'Anan Khalaili': 'Israel', 'Quinten Timber': 'Netherlands',
 'Sebastian Williams': 'England', 'Zavier Gozo': 'United States',
 'Ainsley Maitland-Niles': 'England', 'Kiernan Dewsbury-Hall': 'England',
 'Hayden Hackney': 'England', 'Tyrique George': 'England',
 'César Palacios': 'Spain', 'Ethan Pinnock': 'Jamaica', 'Stephen Mfuni': 'England',
 'Aurèle Amenda': 'Switzerland', 'Caleb Yirenkyi': 'Ghana', 'Haji Wright': 'United States',
 'Loum Tchaouna': 'Chad', 'Yann Gboho': 'Ivory Coast', 'Sidiki Cherif': 'Senegal',
 'Kjell Scherpen': 'Netherlands', 'Issa Diop': 'France', 'Abdoul Ouattara': 'Burkina Faso',
 'Florentino Luís': 'Portugal', 'Exequiel Palacios': 'Argentina', 'Abdul Fatawu': 'Ghana',
 'Sindre Walle Egeli': 'Norway', 'Zian Flemming': 'Netherlands', 'Julio Enciso': 'Paraguay',
 'Emersonn': 'Brazil', 'Chuba Akpom': 'England', 'Daizen Maeda': 'Japan',
 'Jack Butland': 'England', 'Konstantinos Tzolakis': 'Greece',
 'Brooke Norton-Cuffy': 'England', 'Lucas Herrington': 'Australia', 'Matt Targett': 'England',
 'Nobel Mendy': 'Senegal', 'Hidemasa Morita': 'Japan', 'Jens Hjertø-Dahl': 'Norway',
 'Darko Gyabi': 'England', 'Lucas Gourna-Douath': 'France', 'Abdülkadir Ömür': 'Turkey',
 'Christos Mouzakitis': 'Greece', 'Sorba Thomas': 'Wales', 'Elliot Stroud': 'England',
 'Ilyas Ansah': 'Ghana', 'Robinio Vaz': 'Portugal', 'Mohamed-Ali Cho': 'Ivory Coast',
 'John Victor': 'Brazil', 'Steven Benda': 'Germany', 'Xaver Schlager': 'Austria',
 'Liam Delap': 'England', 'Melker Ellborg': 'Sweden', 'Dayann Methalie': 'France',
 'Thomas Meunier': 'Belgium', 'Alan Browne': 'Ireland', 'Jules Ahoka': 'France',
 'Malick Fofana': 'Belgium', 'Juan Riquelme Angulo': 'Ecuador', 'Finlay Herrick': 'England',
 'Airidas Golambeckis': 'Lithuania', 'Ezra Mayers': 'England', 'Divine Mukasa': 'England',
 'Edvin Austbø': 'Norway', 'Joshua Ajala': 'England', 'Lewis Koumas': 'Wales'}

# ---------- parse bundle ----------
env = UnityPy.load(SRC_GD)
assets, objs = {}, {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        b = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
        assets[d.m_Name] = b
        objs[d.m_Name] = obj

raw = assets['Players']
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
max_pid = max(r['pid'] for r in recs)
rec_by_pid = {r['pid']: r for r in recs}
print('players: %d, max pid %d, nations %d' % (len(recs), max_pid, len(nations)))

cp = assets['ClubPlayer']
n1, = struct.unpack_from('<I', cp, 0)
sec1 = {}
for i in range(n1):
    tid, cnt = struct.unpack_from('<II', cp, 4 + i*8)
    sec1[tid] = cnt
sec2 = []
off = 4 + n1*8
while off + 17 <= len(cp):
    tid, p, f1, f2 = struct.unpack_from('<IIII', cp, off)
    sec2.append({'team': tid, 'pid': p, 'jersey': f1, 'f2': f2, 'f3': cp[off+16]})
    off += 17
print('clubplayer: sec1 %d teams, sec2 %d memberships' % (len(sec1), len(sec2)))
orig_sec2 = len(sec2)

_nat_lc = {n.lower().replace('_', ' '): i for i, n in enumerate(nations)}

def nat_idx(name):
    k = (name or 'England').lower().replace('_', ' ')
    return _nat_lc.get(k, _nat_lc.get('england', 0))

# ---------- STEP 2a-pre: OVR corrections (BEFORE rename: resolves original game names) ----------
# ---------- STEP 2a: OVR corrections (verified FC26 values) ----------
ovr_fixed = 0
for u in man['ovr_update']:
    if 'ovr_fc26' not in u:
        continue
    team = u['team_id']
    hits = [p['pid'] for p in sec2 if p['team'] == team]
    byname = {}
    for pid in hits:
        rec = rec_by_pid.get(pid)
        if rec:
            byname.setdefault(rec['name'], []).append(pid)
    pids = byname.get(u['game_name'], [])
    if len(pids) == 1:
        rec = rec_by_pid[pids[0]]
        if rec['attrs'][1] != u['ovr_fc26']:
            rec['attrs'][1] = u['ovr_fc26']
            ovr_fixed += 1
print('STEP2a OVR corrections applied: %d' % ovr_fixed)

# ---------- STEP 1: RENAME (pid-scoped) ----------
renamed = 0
if os.environ.get('ALIGN_NO_RENAME'):
    plan['RENAME'] = {}
for pid_s, real in plan['RENAME'].items():
    rec = rec_by_pid.get(int(pid_s))
    if rec is None:
        print('  RENAME missing pid', pid_s)
        continue
    if rec['name'] != real:
        rec['name'] = real
        renamed += 1
print('STEP1 rename: %d players renamed (of %d planned)' % (renamed, len(plan['RENAME'])))


# ---------- jersey bookkeeping ----------
JERSEY_USED = {}
for tid in sec1:
    JERSEY_USED[tid] = set(p['jersey'] for p in sec2 if p['team'] == tid)

def take_jersey(tid, want):
    used = set(m['jersey'] for m in sec2 if m['team'] == tid)
    if want and want > 0 and want not in used:
        return want
    return next(k for k in range(2, 99) if k not in used)

# ---------- STEP 2b: REMOVE leavers ----------
removed = 0
for r in plan['REMOVE']:
    team, pid = r['team'], r['pid']
    before = len(sec2)
    sec2 = [m for m in sec2 if not (m['team'] == team and m['pid'] == pid)]
    if len(sec2) == before:
        print('  REMOVE no membership found: team %d pid %d' % (team, pid))
        continue
    sec1[team] = sec1.get(team, 1) - 1
    removed += 1
print('STEP2b remove leavers: %d' % removed)

# ---------- STEP 2c: TRANSFER (move existing pid; two-phase so freed numbers recycle) ----------
transferred = 0
pending = []
for t in plan['TRANSFER']:
    pid, src, dst = t['pid'], t['src_team'], t['new_team']
    mem = [m for m in sec2 if m['team'] == src and m['pid'] == pid]
    if not mem:
        print('  TRANSFER source membership missing: team %s pid %s (%s)' % (src, pid, t['src_name']))
        continue
    src_jersey = mem[0]['jersey']
    sec2 = [m for m in sec2 if not (m['team'] == src and m['pid'] == pid)]
    sec1[src] = sec1.get(src, 1) - 1
    pending.append((t, pid, dst, src_jersey))
def _want(t, src_jersey):
    return t['jersey'] or NUM.get(t['real'], 0) or src_jersey

def _free(tid, num):
    return not any(m['team'] == tid and m['jersey'] == num for m in sec2)

def _passkey(item):
    t, pid, dst, src_jersey = item
    w = _want(t, src_jersey)
    return 0 if (w and _free(dst, w)) else 1

pending.sort(key=_passkey)
pass1 = [x for x in pending if _passkey(x) == 0]
pass2 = [x for x in pending if _passkey(x) == 1]
for t, pid, dst, src_jersey in pass1 + pass2:
    jersey = take_jersey(dst, _want(t, src_jersey))
    sec2.append({'team': dst, 'pid': pid, 'jersey': jersey, 'f2': 6912, 'f3': 0})
    sec1[dst] = sec1.get(dst, 0) + 1
    rec = rec_by_pid[pid]
    if t['ovr'] is not None:
        rec['attrs'][1] = t['ovr']
    transferred += 1
    print('  TRANSFER %-16s -> team %d #%d ovr %s' % (t['src_name'], dst, jersey, t['ovr']))
print('STEP2c transfers: %d' % transferred)

# ---------- STEP 2c+: ATTACH (clubless existing pid signs for a club) ----------
attached = 0
for a in plan.get('ATTACH', []):
    pid, team = a['pid'], a['team']
    if any(m['team'] == team and m['pid'] == pid for m in sec2):
        continue
    jersey = take_jersey(team, a['jersey'] or 0)
    sec2.append({'team': team, 'pid': pid, 'jersey': jersey, 'f2': 6912, 'f3': 0})
    sec1[team] = sec1.get(team, 0) + 1
    if a.get('ovr') is not None:
        rec_by_pid[pid]['attrs'][1] = a['ovr']
    attached += 1
    print('  ATTACH pid %d -> team %d #%d' % (pid, team, jersey))
print('STEP2c+ attach: %d' % attached)

# ---------- STEP 2d: INJECT new pids (full teammate-clone + PA record) ----------
club_members = {}
for m in sec2:
    club_members.setdefault(m['team'], []).append(m['pid'])

# ---- parse PlayerAppearanceTable (count + (pid,off) idx + 21B recs) ----
pa_raw = assets['PlayerAppearanceTable']
pa_n, = struct.unpack_from('<I', pa_raw, 0)
pa_idx = [struct.unpack_from('<II', pa_raw, 4 + i*8) for i in range(pa_n)]
pa_idx_map = dict(pa_idx)
pa_data = pa_raw[4 + pa_n*8:]
pa_have = set(pa_idx_map.keys())
print('PA table: %d records' % pa_n)

pa_recs = []   # 21B: pid + 17B app clone
pa_pids = []

def pick_template(tid, pos, ovr):
    pids = [p for p in club_members.get(tid, []) if p in pa_have and p in rec_by_pid]
    if not pids:
        return None
    cands = [rec_by_pid[p] for p in pids]
    if pos == 'GK':
        gk = [c for c in cands if max(c['attrs'][9:13]) >= max(c['attrs'][1], 60)]
        if gk:
            cands = gk
    cands.sort(key=lambda c: abs(c['attrs'][1] - ovr))
    return cands[0]

injected = 0
pid = int(os.environ.get('ALIGN_PID_START', max_pid))
for e in plan['INJECT']:
    pid += 1
    tid = e['team_id']
    nat = nat_idx(e.get('nat') or NAT_OVERRIDE.get(e['name'], 'England'))
    tmpl = pick_template(tid, e['pos'], e['ovr'])
    if tmpl is not None:
        rec = {k: (list(v) if k == 'attrs' else v) for k, v in tmpl.items()}
        rec['pid'] = pid
        rec['name'] = e['name']
        rec['nat'] = nat
        rec['attrs'][1] = e['ovr']
        if e.get('birth'):
            rec['year'] = int(e['birth'])
        dq = DQD.get(e['name'])
        if dq and dq.get('ovr'):
            rec['attrs'][1] = dq['ovr']
        if dq and e['pos'] != 'GK':
            # real six-stat profile (decoded 17B map: 0=PHY 1=OVR 2/3=PAC 4/11/12/16=PAS
            # 5/9/10=DRI 6/13/14=SHO 7/8/15=DEF)
            a = rec['attrs']
            a[0] = dq.get('phy', a[0]); a[2] = a[3] = dq.get('pac', a[2])
            a[4] = a[11] = a[12] = a[16] = dq.get('pas', a[4])
            a[5] = a[9] = a[10] = dq.get('dri', a[5])
            a[6] = a[13] = a[14] = dq.get('sho', a[6])
            a[7] = a[8] = a[15] = dq.get('def', a[7])
        if dq and dq.get('dob'):
            rec['year'] = int(dq['dob'][:4])
        _o = pa_idx_map[tmpl['pid']]  # ABSOLUTE offset into the whole PA blob
        t_app = pa_raw[_o + 4: _o + 21]
    else:
        # neutral fallback: all-zero head model + default PA (device-proven zero-clone)
        rec = {'pid': pid, 'name': e['name'], 'fa': 0, 'fb': 0, 'fc': 0, 'nat': nat,
               'b1': 14, 'b16': 0, 'b0': 6, 'attrs': [70] * 17,
               'tail16': 0, 'tail8': 0, 'year': 2026}
        rec['attrs'][1] = e['ovr']
        app = bytearray(17)
        app[0] = 6; app[1] = 14; app[3] = 255; app[4] = 0
        app[5] = 1; app[6] = 255; app[7] = 127; app[8] = 1
        app[9] = 127; app[14] = 18; app[16] = 127
        t_app = bytes(app)
    recs.append(rec)
    jersey = take_jersey(tid, e['jersey'] or NUM.get(e['name'], 0))
    sec2.append({'team': tid, 'pid': pid, 'jersey': jersey, 'f2': 6912, 'f3': 0})
    sec1[tid] = sec1.get(tid, 0) + 1
    club_members.setdefault(tid, []).append(pid)
    pa_recs.append(struct.pack('<I', pid) + t_app)
    pa_pids.append(pid)
    injected += 1
print('STEP2d injects: %d (pids %d..%d), PA records + %d' % (
    injected, max_pid + 1, pid, len(pa_recs)))

# ---------- REGROUP sec2 by team (importer requires contiguous blocks) ----------
from collections import defaultdict as _dd
_cnt = _dd(int)
for m in sec2:
    _cnt[m['team']] += 1
sec2.sort(key=lambda m: m['team'])
# renumber f2 slots contiguously per team (0,1,2,... x256) - the save importer
# derives per-player squad-list fields from slots; holes/dups from transfers and
# removals corrupt it (missing field2 in player_blob -> dummy cards in UI)
_slot = _dd(int)
for m in sec2:
    m['f2'] = 256 * _slot[m['team']]
    _slot[m['team']] += 1
sec1 = {tid: _cnt.get(tid, 0) for tid in sec1.keys()}
_mono = all(sec2[i]['team'] <= sec2[i+1]['team'] for i in range(len(sec2)-1))
_mism = sum(1 for t in sec1 if sec1[t] != _cnt.get(t, 0))
print('REGROUP: sec2 monotonic=%s, sec1 mismatches=%d' % (_mono, _mism))
assert _mono and _mism == 0

# ---------- serialize ----------
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
players_raw = out.getvalue()

out = io.BytesIO()
out.write(struct.pack('<I', len(sec1)))
for tid, cnt in sec1.items():
    out.write(struct.pack('<II', tid, cnt))
for r in sec2:
    out.write(struct.pack('<IIII', r['team'], r['pid'], r['jersey'], r['f2']))
    out.write(bytes([r['f3']]))
clubplayer_raw = out.getvalue()

# build new PlayerAppearanceTable bytes
k_pa = len(pa_recs)
base_off = 4 + (pa_n + k_pa) * 8 + len(pa_data)
pa_out = io.BytesIO()
pa_out.write(struct.pack('<I', pa_n + k_pa))
for kk, oo in pa_idx:
    pa_out.write(struct.pack('<II', kk, oo + 8 * k_pa))
for j, pr in enumerate(pa_recs):
    pa_out.write(struct.pack('<II', pa_pids[j], base_off + j * 21))
pa_out.write(pa_data)
pa_out.write(b''.join(pa_recs))
pa_raw = pa_out.getvalue()
print('PA table written: %d -> %d records' % (pa_n, pa_n + k_pa))

shutil.copyfile(SRC_GD, OUT_GD)
env2 = UnityPy.load(OUT_GD)
n_written = 0
for obj in env2.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'Players':
            d.m_Script = players_raw.decode('utf-8', errors='surrogateescape')
            d.save(); n_written += 1
        elif d.m_Name == 'ClubPlayer':
            d.m_Script = clubplayer_raw.decode('utf-8', errors='surrogateescape')
            d.save(); n_written += 1
        elif d.m_Name == 'PlayerAppearanceTable':
            d.m_Script = pa_raw.decode('utf-8', errors='surrogateescape')
            d.save(); n_written += 1
with open(OUT_GD, 'wb') as f:
    f.write(env2.file.save())
print('bundle written: %s (%d assets patched)' % (OUT_GD, n_written))

# ---------- verify: re-parse ----------
env3 = UnityPy.load(OUT_GD)
for obj in env3.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'ClubPlayer'):
            raw = d.m_Script
            raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
            if d.m_Name == 'Players':
                off2 = 8
                nc2, = struct.unpack_from('<H', raw, off2); off2 += 2
                for _ in range(nc2):
                    ln, = struct.unpack_from('<H', raw, off2); off2 += 2 + ln*2
                pc2, = struct.unpack_from('<I', raw, off2)
                print('VERIFY Players: %d (was %d, +%d)' % (pc2, pcnt, pc2 - pcnt))
            else:
                n1b, = struct.unpack_from('<I', raw, 0)
                body = len(raw) - (4 + n1b*8)
                print('VERIFY ClubPlayer: sec2 %d (was %d, %+d)' % (
                    body // 17, orig_sec2, body // 17 - orig_sec2))

# ---------- verify: invariant - every club-member pid has Players rec + PA entry ----------
env4 = UnityPy.load(OUT_GD)
v_players, v_cp, v_pa = {}, None, set()
v_pa_idx, v_pa_size = [], 0
for obj in env4.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        raw = d.m_Script
        raw = raw.encode('utf-8', errors='surrogateescape') if isinstance(raw, str) else bytes(raw)
        if d.m_Name == 'Players':
            o = 8
            nc, = struct.unpack_from('<H', raw, o); o += 2
            for _ in range(nc):
                ln, = struct.unpack_from('<H', raw, o); o += 2 + ln * 2
            pc, = struct.unpack_from('<I', raw, o); o += 4
            for _ in range(pc):
                p, = struct.unpack_from('<I', raw, o); o += 4
                ln, = struct.unpack_from('<H', raw, o); o += 2
                nm = raw[o:o+ln*2].decode('utf-16-le', errors='replace')
                o += ln * 2 + 8 + 3 + 17 + 2 + 1 + 4
                v_players[p] = nm
        elif d.m_Name == 'ClubPlayer':
            v_cp = raw
        elif d.m_Name == 'PlayerAppearanceTable':
            v_pa_size = len(raw)
            n, = struct.unpack_from('<I', raw, 0)
            v_pa_idx = [struct.unpack_from('<II', raw, 4 + i * 8) for i in range(n)]
            for kk, _oo in v_pa_idx:
                v_pa.add(kk)
mem_total = missing_pa = missing_rec = 0
off = 4
n1c, = struct.unpack_from('<I', v_cp, 0)
off = 4 + n1c * 8
while off + 17 <= len(v_cp):
    tid, p, f1, f2 = struct.unpack_from('<IIII', v_cp, off)
    mem_total += 1
    if p not in v_pa:
        missing_pa += 1
    if p not in v_players:
        missing_rec += 1
    off += 17
dup = len(v_players) != len(set(v_players.keys()))
rows2 = []
off = 4 + n1c * 8
while off + 17 <= len(v_cp):
    rows2.append(struct.unpack_from('<IIII', v_cp, off)[0]); off += 17
mono2 = all(rows2[i] <= rows2[i+1] for i in range(len(rows2)-1))
print('INVARIANT: output sec2 monotonic=%s' % mono2)
assert mono2
bad_off = [p for p, o in [(kk, oo) for kk, oo in v_pa_idx] if o + 21 > v_pa_size]
print('INVARIANT: PA idx entries %d | offset-overflow %d' % (len(v_pa_idx), len(bad_off)))
assert not bad_off, 'PA OFFSET OVERFLOW: %s' % bad_off[:5]
print('INVARIANT: members %d | no-PA %d | no-record %d | dup-pid %s' % (
    mem_total, missing_pa, missing_rec, dup))
assert missing_pa == 0 and missing_rec == 0 and not dup, 'INVARIANT BROKEN'
print('DONE')
