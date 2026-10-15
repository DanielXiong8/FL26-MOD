# -*- coding: utf-8 -*-
"""jobs.py — simple in-process job queue with run provenance.
States: QUEUED -> RUNNING -> PASS | FAIL | CANCELLED. One active build at a time."""
import json, os, threading, time, traceback

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
RUNS = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'runs')

_lock = threading.Lock()
_jobs = {}          # job_id -> dict
_queue = []         # job_ids in order
_worker = None      # thread handle
_active = None


def _now():
    return time.strftime('%Y%m%d_%H%M%S')


def new_job(jtype, payload):
    with _lock:
        run_id = '%s_%s' % (jtype, _now())
        run_dir = os.path.join(RUNS, 'runs', '%ss' % jtype, run_id)
        os.makedirs(run_dir, exist_ok=True)
        job = {'id': run_id, 'type': jtype, 'state': 'QUEUED',
               'created': _now(), 'run_dir': run_dir, 'payload': payload,
               'stages': [], 'error': None, 'log_path': os.path.join(run_dir, 'log.txt')}
        with open(os.path.join(run_dir, 'request.json'), 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        _jobs[run_id] = job
        _queue.append(run_id)
        return job


def get(job_id):
    with _lock:
        return json.loads(json.dumps(_jobs.get(job_id)), ) if job_id in _jobs else None


def list_jobs(jtype=None, limit=20):
    with _lock:
        ids = [j for j in _queue if jtype is None or _jobs[j]['type'] == jtype]
        return [_jobs[j] for j in ids[-limit:]]


def stage(job_id, name, state, detail=''):
    """Update one pipeline stage: name + state(PENDING/RUNNING/PASS/FAIL) + detail."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for st in job['stages']:
            if st['name'] == name:
                st['state'] = state
                st['detail'] = detail
                break
        else:
            job['stages'].append({'name': name, 'state': state, 'detail': detail})


def set_error(job_id, err):
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job['error'] = str(err)
            job['state'] = 'FAIL'


def log(job_id, msg):
    with _lock:
        job = _jobs.get(job_id)
    if job:
        with open(job['log_path'], 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%H:%M:%S'), msg))


def run_queue(worker_fn):
    """worker_fn(job) executes the job's stages; called in a background thread."""
    global _worker, _active

    def loop():
        global _active
        while True:
            with _lock:
                nxt = next((j for j in _queue if _jobs[j]['state'] == 'QUEUED'), None)
            if not nxt:
                time.sleep(0.5)
                continue
            with _lock:
                job = _jobs[nxt]
                job['state'] = 'RUNNING'
                _active = nxt
            try:
                worker_fn(job)
                with _lock:
                    if job['state'] == 'RUNNING':
                        job['state'] = 'PASS'
            except Exception as ex:
                traceback.print_exc()
                set_error(nxt, ex)
                log(nxt, 'EXCEPTION: %r' % ex)
            finally:
                with _lock:
                    _active = None
                # persist final snapshot
                with _lock:
                    snap = json.loads(json.dumps(_jobs[nxt]))
                with open(os.path.join(snap['run_dir'], 'result.json'), 'w', encoding='utf-8') as f:
                    json.dump(snap, f, ensure_ascii=False, indent=1)

    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=loop, daemon=True)
        _worker.start()
