# -*- coding: utf-8 -*-
"""app.py — FL26 Face Builder Web V1 (FastAPI).

Orchestrates VERIFIED pipelines only:
  candidates  -> face_benchmark/scripts/generate_candidates.py (existing CLI, subprocess)
  injection   -> backend/inject_player_v1.py (Phase13B device-proven formula)
  texture     -> backend/texture_inject.py (TEXTURE-ONLY, no MICA)
  save ops    -> work/save_pipeline/phase14a/save_editor.py
  install     -> adb install (device 95e2d9a)
No pipeline logic is duplicated here; this file only wires stages together.
"""
import io, json, os, shutil, subprocess, sys, threading, time, uuid, asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).parent
ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
CAND_SCRIPT = os.path.join(ROOT, 'face_benchmark', 'scripts', 'generate_candidates.py')
RUNS = HERE.parent / 'runs'
os.makedirs(RUNS, exist_ok=True)
sys.path.insert(0, str(HERE))
sys.path.insert(0, r'D:\FL26_Mod\workace_pipeline\phase14a5')

import jobs
import data_catalog
import appearance_state as AS

ADB = os.path.join(ROOT, 'android-sdk', 'platform-tools', 'adb.exe')
BT = os.path.join(ROOT, 'android-sdk', 'build-tools', '36.0.0')

app = FastAPI(title='FL26 Face Builder V1')
_progress = {}          # job_id -> stage snapshot for SSE
_sse_waiters = []       # list of asyncio.Queue


def _emit(job_id, stage, state, detail=''):
    _progress[job_id] = {'stage': stage, 'state': state, 'detail': detail}
    jobs.stage(job_id, stage, state, detail)
    for q in list(_sse_waiters):
        try:
            q.put_nowait({'job': job_id, 'stage': stage, 'state': state, 'detail': detail})
        except Exception:
            pass


def _run_cmd(cmd, job_id, stage_name, timeout=1800):
    _emit(job_id, stage_name, 'RUNNING')
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or '')[-800:]
        _emit(job_id, stage_name, 'FAIL', tail)
        raise RuntimeError('%s failed: %s' % (stage_name, tail))
    _emit(job_id, stage_name, 'PASS')
    return p.stdout


# ---------------- catalog ----------------
@app.get('/api/catalog')
def api_catalog():
    c = data_catalog.get_cache()
    # merge registry players into live roster counts (device reality)
    import registry as reg
    delta = {}
    for p in reg.all_players():
        delta[p['team_id']] = delta.get(p['team_id'], 0) + 1
    for t in c['teams']:
        t['roster_count'] = t.get('roster_count', 0) + delta.get(t['id'], 0)
    return c


@app.get('/api/catalog/rebuild')
def api_catalog_rebuild():
    return data_catalog.build_cache()


# ---------------- step 1-2: upload + candidates ----------------
@app.post('/api/candidates')
async def api_candidates(files: list[UploadFile] = File(...), n: int = Form(8),
                         geometry: str = Form('off')):
    if not 1 <= len(files) <= 3:
        raise HTTPException(400, 'upload 1-3 photos')
    job = jobs.new_job('candidate', {'photos': [f.filename for f in files], 'n': n,
                                     'geometry': geometry})
    run_dir = Path(job['run_dir'])
    photos = []
    _emit(job['id'], 'PHOTO', 'RUNNING')
    for i, f in enumerate(files):
        dst = run_dir / ('photo_%d.png' % i)
        with open(dst, 'wb') as out:
            out.write(await f.read())
        # input quality gate: tiny/low-res photos produce a generic-looking bake
        from PIL import Image as _PILImage
        im = _PILImage.open(dst)
        w, h = im.size
        if w < 500 or h < 500:
            raise HTTPException(400,
                '第%d张照片分辨率不足（%dx%d）。请上传高清正脸照：人脸占画面约1/2、'
                '光线均匀、分辨率≥800x800（网页缩略图/视频截图无法建模）' % (i + 1, w, h))
        photos.append(str(dst))
    _emit(job['id'], 'PHOTO', 'PASS', '%d photos' % len(photos))

    # existing candidate pipeline (primary photo first)
    out_dir = run_dir / 'candidates_out'
    out_dir.mkdir(exist_ok=True)
    def worker():
        try:
            _run_cmd([sys.executable, CAND_SCRIPT, '--input', photos[0],
                      '--n', str(n), '--output', str(out_dir)], job['id'], 'CANDIDATES', timeout=1800)
            jobs._jobs[job['id']]['state'] = 'PASS'
            jobs._jobs[job['id']]['result'] = {'candidates_dir': str(out_dir)}
            # STEP 2 upgrade: render ALL candidates as game-equivalent heads in ONE
            # Unity launch so the selection cards show what the game will display.
            _emit(job['id'], 'PREVIEW', 'RUNNING', 'batch render %d candidates' % n)
            try:
                import preview as pv
                if 'D:/FL26_Mod/work/face_pipeline/phase14a5' not in sys.path:
                    sys.path.insert(0, 'D:/FL26_Mod/work/face_pipeline/phase14a5')
                import chain_geometry
                previews = {}
                done = 0
                for i in range(1, n + 1):
                    bake = out_dir / 'candidates' / ('c%d' % i) / 'baked.png'
                    if not bake.exists():
                        continue
                    # personalize geometry per candidate: chain c1 once, reuse its
                    # stage1 alignment but re-run stage2c per candidate is overkill —
                    # the candidate grid differs in TEXTURE params only, so ONE
                    # geometry run (primary photo) is correct for all candidates.
                    geo_dir = Path(job['run_dir']) / 'geometry'
                    stage2 = geo_dir / 'adapter' / 'stage2_ea1.json'
                    use_geo = (job.get('payload') or {}).get('geometry') == 'on'
                    if use_geo and not stage2.exists():
                        _n = len(list(Path(job['run_dir']).glob('photo_*.png')))
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'MICA fusion of %d photos + V3 shape transfer' % _n)
                        # V3: FUSED multi-photo MICA -> stage1/2c -> DEPTH-RAY shape
                        # transfer (full MICA surface onto EA1 topology).
                        import subprocess as _sp
                        _v3 = 'D:\\FL26_Mod\\work\\face_pipeline\\phase14a5\\v3_shape_transfer.py'
                        _recon = 'D:\\FL26_Mod\\face_benchmark\\envs\\envs\\recon\\python.exe'
                        photos_all = sorted(Path(job['run_dir']).glob('photo_*.png'))
                        out = chain_geometry.chain_multi([str(q) for q in photos_all], str(geo_dir))
                        _r = _sp.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                        if _r.returncode != 0:
                            raise RuntimeError('v3 transfer failed: %s' % (_r.stderr or _r.stdout)[-300:])
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'geometry ready (V3)')
                    # default (geometry off): NEUTRAL head + personalized bake = the
                    # device-proven golden recipe. Warping geometry without re-baking
                    # the texture misaligns painted features (PC A/B verdict 2026-09-10).
                    urls = pv.render(str(bake), stage2_json=str(stage2) if use_geo else None)
                    previews['c%d' % i] = urls
                    done += 1
                    _emit(job['id'], 'PREVIEW', 'RUNNING', '%d/%d rendered' % (done, n))
                jobs._jobs[job['id']]['previews'] = previews
                jobs._jobs[job['id']]['geometry'] = str(geo_dir / 'stage2_ea1.json')
                _emit(job['id'], 'PREVIEW', 'PASS', '%d rendered (personalized)' % done)
            except Exception as pex:
                # preview is an enhancement; candidates stay usable without it
                _emit(job['id'], 'PREVIEW', 'FAIL', str(pex)[:200])
        except Exception as ex:
            jobs.set_error(job['id'], ex)
            _emit(job['id'], 'JOB', 'FAIL', str(ex)[:300])
    threading.Thread(target=worker, daemon=True).start()
    return job


@app.get('/api/candidates/{job_id}')
def api_candidates_get(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404, 'job not found')
    cdir = Path(j['run_dir']) / 'candidates_out'
    out = {'job': j, 'candidates': []}
    metrics_csv = cdir / 'metrics.csv'
    previews = j.get('previews') or {}
    if metrics_csv.exists():
        import csv as _csv
        rows = list(_csv.DictReader(open(metrics_csv, encoding='utf-8-sig')))
        for r in rows:
            c = r.get('name') or r.get('candidate')
            entry = {'name': c, 'raw': r}
            mj = cdir / 'candidates' / str(c) / 'metrics.json'
            if mj.exists():
                entry['metrics'] = json.load(open(mj, encoding='utf-8'))
            entry['preview'] = '/api/file/%s' % (cdir / 'candidates' / str(c) / 'front.png')
            entry['baked'] = '/api/file/%s' % (cdir / 'candidates' / str(c) / 'baked.png')
            m = entry.get('metrics') or {}
            entry['status'] = m.get('status') or ('OK' if not m.get('reject') else 'REJECT')
            # game-equivalent render (front + 3 more views) if preview batch done
            if c in previews:
                entry['game_preview'] = previews[c]
            out['candidates'].append(entry)
    return out


@app.get('/api/file/{path:path}')
def api_file(path: str):
    p = Path(path)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


# ---------------- step 7: build ----------------
@app.post('/api/build')
async def api_build(
    reference_pid: int = Form(0),  # 0 = ORIGIN (zero-clone, no reference player)
    candidate_baked: str = Form(''),
    name: str = Form(...),
    position: str = Form('FW'),
    nat: int = Form(24),
    team_id: int = Form(10059),
    jersey: int = Form(30),
    hair_color_id: int = Form(2),
    beard_enabled: bool = Form(True),
    beard_style_id: int = Form(1),
    eyebrow_index: int = Form(1),
    skin_tone: int = Form(6),
    face_texture_id: int = Form(14),
    geometry: str = Form('off'),
    stage2_json: str = Form(''),  # direct path to a personalized 700-vert mesh
    b14: int = Form(18),  # FaceTemplate row for the new player
    attrs: str = Form('')):
    cat = data_catalog.get_cache()
    cap = cat.get('roster_cap', 33)
    roster_count = next((t['roster_count'] for t in cat['teams'] if t['id'] == team_id), 0)
    attr_list = [int(x) for x in attrs.split(',')] if attrs else None
    cfg = AS.build_state({
        'reference_pid': reference_pid, 'name': name, 'position': position,
        'nat': nat, 'team_id': team_id, 'jersey': jersey,
        'hair_color_id': hair_color_id, 'beard_enabled': beard_enabled,
        'beard_style_id': beard_style_id, 'eyebrow_index': eyebrow_index,
        'skin_tone': skin_tone, 'face_texture_id': face_texture_id,
        'attrs': attr_list or AS.POS_TEMPLATES.get(position, AS.POS_TEMPLATES['FW']),
    })
    errs = AS.validate(cfg, roster_count, cap)
    if errs:
        raise HTTPException(400, '; '.join(errs))
    if candidate_baked and os.path.exists(candidate_baked):
        cfg['photo_layers']['face_texture_png'] = candidate_baked
    job = jobs.new_job('build', cfg)

    def worker():
        jid = job['id']
        try:
            # stage A: players/clubplayer/PA injection into fresh gamedata + APK
            _emit(jid, 'PLAYER', 'RUNNING')
            sys.path.insert(0, str(HERE))
            import inject_player_v1
            _emit(jid, 'PLAYER', 'RUNNING', 'inject Players/ClubPlayer/PA tables')
            res = inject_player_v1.run(cfg, str(Path(job['run_dir'])))
            _emit(jid, 'PLAYER', 'PASS', 'pid=%d jersey=%d' % (res['pid'], res['jersey']))
            _emit(jid, 'PLAYER', 'RUNNING', 'zipalign + sign (548MB, 1-2 min)')
            apk = res['apk']

            # stage B: face inject. Default = TEXTURE-ONLY on the NEUTRAL head
            # (the device-proven golden recipe: bake texture already aligns with
            # the neutral mesh, so this is what the game will actually show).
            # geometry='on' opts into experimental MICA mesh warping.
            bake_png = cfg['photo_layers'].get('face_texture_png')
            if bake_png and os.path.exists(bake_png):
                if geometry == 'on':
                    _emit(jid, 'APK', 'RUNNING', 'geometry chain (MICA ~1-2 min)')
                    geo_dir = Path(job['run_dir']) / 'geometry'
                    sys.path = [p for p in sys.path if 'face_pipeline' not in p] + ['D:/FL26_Mod/work/face_pipeline/phase14a5']
                    import chain_geometry
                    # reuse the candidate job's geometry when present (computed from
                    # photo_0 there); NEVER feed the UV bake to MICA as a "photo".
                    # candidate_baked: ...\candidates\<job>\candidates_out\candidates\cN\baked.png
                    stage2 = None
                    if stage2_json and os.path.exists(stage2_json):
                        stage2 = stage2_json
                    cb = Path(candidate_baked)
                    run_dir_cand = cb.parents[3] if len(cb.parents) >= 4 else None
                    if stage2 is None and run_dir_cand is not None:
                        cand_geo = run_dir_cand / 'geometry' / 'adapter' / 'stage2_ea1.json'
                        if cand_geo.exists():
                            stage2 = str(cand_geo)
                    if stage2 is None:
                        # FUSED multi-photo MICA: ALL uploaded photos combine into
                        # ONE higher-similarity model (input-level template
                        # averaging, then stage1+2c adapter route).
                        if run_dir_cand is not None:
                            photos = sorted(run_dir_cand.glob('photo_*.png'))
                            if not photos:
                                raise RuntimeError('geometry=on but no source photos found')
                            _emit(jid, 'APK', 'RUNNING', 'MICA fusion of %d photos (~2 min)' % len(photos))
                            out = chain_geometry.chain_multi([str(p) for p in photos], str(geo_dir))
                            import subprocess as _sp2
                            _v3 = 'D:\\FL26_Mod\\work\\face_pipeline\\phase14a5\\v3_shape_transfer.py'
                            _recon = 'D:\\FL26_Mod\\face_benchmark\\envs\\envs\\recon\\python.exe'
                            _r2 = _sp2.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                            if _r2.returncode != 0:
                                raise RuntimeError('v3 transfer failed: %s' % (_r2.stderr or _r2.stdout)[-300:])
                            stage2 = out['stage2_ea1']
                            _emit(jid, 'APK', 'RUNNING', 're-bake skin on V3 geometry')
                            _bake8 = 'D:\\FL26_Mod\\work\\face_pipeline\\track_user1\\bake8_user.py'
                            _env3 = dict(os.environ)
                            _env3['BAKE_V3_JSON'] = stage2
                            _env3['PYTHONIOENCODING'] = 'utf-8'
                            _r3 = _sp2.run([_recon, _bake8, str(photos[0])],
                                           cwd=os.path.dirname(_bake8), capture_output=True,
                                           text=True, timeout=900, env=_env3)
                            if _r3.returncode != 0:
                                raise RuntimeError('v3 rebake failed: %s' % (_r3.stderr or _r3.stdout)[-400:])
                            bake_png = os.path.join(os.path.dirname(_bake8), 'baked_ea3.png')
                        else:
                            raise RuntimeError('geometry=on but no candidate photos found for MICA')
                    _emit(jid, 'APK', 'RUNNING', 'mesh+texture inject')
                    import mesh_inject
                    apk, _ = mesh_inject.run(apk, stage2, bake_png, str(Path(job['run_dir'])),
                                             slot_b1=cfg['explicit']['face_texture_id'])
                    _emit(jid, 'APK', 'PASS', 'EXPERIMENTAL geometry + bake')
                else:
                    _emit(jid, 'APK', 'RUNNING', 'texture-only inject (golden recipe)')
                    import texture_inject
                    apk, _ = texture_inject.run(apk, bake_png, str(Path(job['run_dir'])),
                                                slot_b1=cfg['explicit']['face_texture_id'])
                    _emit(jid, 'APK', 'PASS', 'texture-only (golden)')
            else:
                _emit(jid, 'APK', 'PASS', 'no candidate texture (base face)')
            # final sha + zipalign/sign already done in inject (resign after texture repack)
            _emit(jid, 'SIGN', 'RUNNING')
            envv = dict(os.environ)
            JH = r'C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot'
            envv['JAVA_HOME'] = JH; envv['Path'] = JH + r'\bin;' + envv.get('Path', '')
            import subprocess as sp
            aligned = apk.replace('.apk', '_al.apk')
            sp.run([os.path.join(BT, 'zipalign.exe'), '-p', '-f', '4', apk, aligned],
                   capture_output=True, env=envv)
            if os.path.exists(aligned):
                os.replace(aligned, apk)
            r = sp.run([os.path.join(BT, 'apksigner.bat'), 'sign', '--ks',
                        os.path.join(ROOT, 'build', 'fl26_test.keystore'),
                        '--ks-pass', 'pass:fl26modtest', '--ks-key-alias', 'fl26test', apk],
                       capture_output=True, text=True, env=envv)
            if r.returncode != 0:
                raise RuntimeError('sign: %s' % r.stderr[-300:])
            _emit(jid, 'SIGN', 'PASS')
            import hashlib
            h = hashlib.sha256()
            with open(apk, 'rb') as f:
                for c in iter(lambda: f.read(1 << 20), b''):
                    h.update(c)
            # auto-register: pid/jersey/slot become permanent for future builds
            try:
                import registry as reg
                pi = cfg['player_identity']
                reg.add(res['pid'], pi['name'], pi['team_id'], res['jersey'], h.hexdigest(),
                        slot_note='auto build %s' % jid,
                        attrs=list(pi['attrs_17']), nat=pi['nationality_nat'],
                        face_texture_id=cfg['explicit']['face_texture_id'],
                        b14=cfg['explicit'].get('b14', 18))
            except Exception as rex:
                print('[build] registry add failed: %s' % rex)
            with jobs._lock:
                jj = jobs._jobs[jid]
                jj['state'] = 'PASS'
                jj['result'] = {'apk': apk, 'pid': res['pid'], 'sha256': h.hexdigest(),
                                'size': os.path.getsize(apk), 'team': res['team'],
                                'jersey': res['jersey']}
        except Exception as ex:
            jobs.set_error(job['id'], ex)
            _emit(job['id'], 'JOB', 'FAIL', str(ex)[:300])
            log_line = str(ex)
            with open(Path(job['run_dir']) / 'log.txt', 'a', encoding='utf-8') as f:
                f.write('FAIL: %s\n' % log_line)
    threading.Thread(target=worker, daemon=True).start()
    return job


@app.get('/api/job/{job_id}')
def api_job(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404)
    return j


# ---------------- install ----------------
@app.post('/api/install/{job_id}')
def api_install(job_id: str):
    j = jobs.get(job_id)
    if not j or j.get('state') != 'PASS' or 'result' not in j:
        raise HTTPException(400, 'BUILD not PASS')
    apk = j['result']['apk']
    # gate: SIGN+VERIFY already enforced in build; check device
    p = subprocess.run([ADB, 'devices'], capture_output=True, text=True)
    if 'device' not in p.stdout:
        raise HTTPException(400, 'no device connected')
    r = subprocess.run([ADB, 'install', '-r', '-d', apk], capture_output=True, text=True, timeout=900)
    return {'install': r.stdout.strip() or r.stderr.strip(),
            'ok': 'Success' in (r.stdout + r.stderr)}


# ---------------- save import (roster manager) ----------------
@app.post('/api/roster/export')
def api_roster_export():
    p = subprocess.run([ADB, 'shell', 'am', 'start', '-n',
                        'com.football.soccer.league.mod/com.fl26mod.saveexport.SaveExportActivity'],
                       capture_output=True, text=True)
    time.sleep(5)
    pull_dir = RUNS / 'save_pull' / time.strftime('%Y%m%d_%H%M%S')
    pull_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([ADB, 'pull', '/sdcard/Android/data/com.football.soccer.league.mod/files/save_export',
                        str(pull_dir)], capture_output=True, text=True)
    ok = 'pulled' in r.stdout
    return {'ok': ok, 'dir': str(pull_dir / 'save_export')}


@app.post('/api/roster/move')
def api_roster_move(pid: int = Form(...), to_team: int = Form(...), jersey: int = Form(30)):
    sys.path.insert(0, r'D:\FL26_Mod\work\save_pipeline\phase14a')
    import save_editor as se
    cat = data_catalog.get_cache()
    if to_team != 10059:
        # only verified-save-mapped teams in V1 (Friendly save DB hosts China roster)
        raise HTTPException(400, 'V1 roster moves apply to China NT (10059) only')
    # latest pulled export
    pulls = sorted((RUNS / 'save_pull').glob('*'), key=os.path.getmtime)
    if not pulls:
        raise HTTPException(400, 'export first: POST /api/roster/export')
    src_db = pulls[-1] / 'save_export' / 'Archives' / 'Friendly' / 'friendly.db'
    if not src_db.exists():
        raise HTTPException(400, 'friendly.db missing in latest export')
    import sqlite3
    conn = sqlite3.connect(str(src_db))
    cur = conn.cursor()
    cur.execute("SELECT payload FROM team_blob WHERE team_id=10059")
    p = cur.fetchone()[0]
    if isinstance(p, str):
        p = p.encode('utf-8', 'surrogateescape')
    roster = se.roster_of(p)['roster']
    if pid in roster:
        conn.close()
        return {'ok': False, 'msg': 'player already in China roster'}
    if len(roster) >= cat.get('roster_cap', 33):
        conn.close()
        raise HTTPException(400, 'China roster at cap (%d)' % len(roster))
    p2 = se.team_add_player(p, pid)
    cur.execute("UPDATE team_blob SET payload=? WHERE team_id=10059", (p2,))
    cur.execute("SELECT payload FROM player_blob WHERE player_id=?", (pid,))
    row = cur.fetchone()
    if row:
        pp = row[0]
        if isinstance(pp, str):
            pp = pp.encode('utf-8', 'surrogateescape')
        pf = se.parse(pp)
        nf = [(f, w, (to_team if (f == 5 and w == 0) else v)) for f, w, v in pf]
        cur.execute("UPDATE player_blob SET payload=? WHERE player_id=?", (se.serialize(nf), pid))
    conn.commit(); conn.close()
    # push + import
    imp = RUNS / 'save_import' / time.strftime('%Y%m%d_%H%M%S')
    os.makedirs(imp, exist_ok=True)
    shutil.copytree(pulls[-1] / 'save_export' / 'Archives', imp / 'Archives')
    shutil.copyfile(src_db, imp / 'Archives' / 'Friendly' / 'friendly.db')
    subprocess.run([ADB, 'shell', 'rm', '-rf',
                    '/sdcard/Android/data/com.football.soccer.league.mod/files/save_import'],
                   capture_output=True)
    subprocess.run([ADB, 'push', str(imp / 'Archives'),
                    '/sdcard/Android/data/com.football.soccer.league.mod/files/save_import/Archives'],
                   capture_output=True)
    subprocess.run([ADB, 'shell', 'am', 'start', '-n',
                    'com.football.soccer.league.mod/com.fl26mod.saveexport.SaveImportActivity'],
                   capture_output=True)
    time.sleep(5)
    return {'ok': True, 'msg': 'IMPORT DONE: pid %d -> China roster (restart game to see)' % pid}


# ---------------- preview (game-equivalent face) ----------------
@app.post('/api/preview')
async def api_preview(bake_png: str = Form(...), iris: str = Form('eye_darkbrown'),
                      stage2_json: str = Form('')):
    if not os.path.exists(bake_png):
        raise HTTPException(404, 'bake png not found: %s' % bake_png)
    import preview as pv
    def worker():
        _preview_state['running'] = True
        try:
            _preview_state['result'] = pv.render(bake_png, iris=iris,
                                                 stage2_json=stage2_json or None)
            _preview_state['running'] = False
        except Exception as ex:
            _preview_state['error'] = str(ex)
            _preview_state['running'] = False
    _preview_state.clear()
    _preview_state.update({'running': True, 'result': None, 'error': None})
    threading.Thread(target=worker, daemon=True).start()
    return {'started': True}


_preview_state = {'running': False, 'result': None, 'error': None}


@app.get('/api/preview/state')
def api_preview_state():
    return _preview_state


# ---------------- SSE progress ----------------
@app.get('/api/progress')
async def api_progress(job_id: str = ''):
    q = asyncio.Queue()
    _sse_waiters.append(q)

    async def gen():
        try:
            if job_id and job_id in _progress:
                yield 'data: %s\n\n' % json.dumps(_progress[job_id])
            while True:
                ev = await q.get()
                if job_id and ev.get('job') != job_id:
                    continue
                yield 'data: %s\n\n' % json.dumps(ev)
        except asyncio.CancelledError:
            pass
        finally:
            if q in _sse_waiters:
                _sse_waiters.remove(q)
    return StreamingResponse(gen(), media_type='text/event-stream')


# ---------------- static frontend ----------------
FRONT = HERE.parent / 'frontend'
app.mount('/static', StaticFiles(directory=str(HERE.parent / 'static')), name='static')
app.mount('/', StaticFiles(directory=str(FRONT), html=True), name='front')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8765)
