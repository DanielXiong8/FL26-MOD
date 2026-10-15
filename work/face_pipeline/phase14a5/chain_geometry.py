# -*- coding: utf-8 -*-
"""chain_geometry.py — photo → personalized face geometry, one command (Phase 14A.5).

Orchestrates the device-verified geometry chain for ONE photo:
  1. MICA single-photo reconstruction  (recon env, run_mica_single.py)
     -> outputs/mica/<run>/mesh.obj + identity.npy + kpt68.npy (5023v, mm)
  2. Stage1 alignment                  (adapter_stage1.py, patched paths)
     -> stage1_alignment.json (FL26 se3 template <-> FLAME 68kpt)
  3. Stage2c EA1 adaptation            (adapter_stage2c_ea1.py, patched paths)
     -> stage2_ea1.json (700-vert personalized face mesh, mm)
  4. Validation: mesh.obj + stage2 json present, vert count == 700

Usage:
  python chain_geometry.py --photo D:\...\face.jpg --run D:\...\runs\geo_<id>

Everything is written under --run; NO protected assets are modified. The adapter
scripts are executed from COPIES with per-run paths patched in memory.
"""
import argparse, json, os, re, shutil, subprocess, sys

FB = os.path.join(os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'), 'face_benchmark')
RECON_PY = os.path.join(FB, 'envs', 'envs', 'recon', 'python.exe')
SCRIPTS = os.path.join(FB, 'scripts')
RUN_MICA = os.path.join(SCRIPTS, 'run_mica_single.py')


def log(msg):
    print('[chain] %s' % msg, flush=True)


def read_text(p):
    return open(p, encoding='utf-8', errors='replace').read()


def write_text(p, s):
    open(p, 'w', encoding='utf-8').write(s)


def run_step(cmd, name, cwd=None, timeout=900):
    log('%s running...' % name)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or '')[-900:]
        raise RuntimeError('%s failed (exit %s):\n%s' % (name, r.returncode, tail))
    log('%s OK' % name)
    return r.stdout


def chain_multi(photos, run_dir):
    """N-photo chain: FUSED MICA (input-level template averaging) -> stage1 -> 2c."""
    os.makedirs(run_dir, exist_ok=True)
    ad_out = os.path.join(run_dir, 'adapter')
    os.makedirs(ad_out, exist_ok=True)
    multi_dir = run_dir + '_multi'
    RUN_MULTI = os.path.join(SCRIPTS, 'run_mica_multi.py')
    run_step([RECON_PY, RUN_MULTI, '--photos'] + list(photos) + ['--out', multi_dir],
             'MICA_MULTI', cwd=os.path.join(FB, 'repos', 'MICA'), timeout=1200)
    mica_out = os.path.join(multi_dir, 'fused_input')
    os.makedirs(os.path.join(run_dir, 'mica'), exist_ok=True)
    for fn in ('mesh.obj', 'mesh.ply', 'identity.npy', 'kpt68.npy'):
        src = os.path.join(mica_out, fn)
        assert os.path.exists(src), 'fused %s missing' % fn
        shutil.copyfile(src, os.path.join(run_dir, 'mica', fn))
    s1_json, s2_json = _adapter_stage(run_dir, ad_out)
    return {'mica_dir': os.path.join(run_dir, 'mica'), 'adapter_dir': ad_out,
            'stage2_ea1': s2_json, 'stage1': s1_json,
            'mesh_obj': os.path.join(run_dir, 'mica', 'mesh.obj')}


def chain(photo, run_dir):
    os.makedirs(run_dir, exist_ok=True)
    mica_out = os.path.join(run_dir, 'mica')
    ad_out = os.path.join(run_dir, 'adapter')

    # ---- 1. MICA single-photo ----
    run_step([RECON_PY, RUN_MICA, '--photo', photo, '--out', mica_out], 'MICA',
             cwd=os.path.join(FB, 'repos', 'MICA'), timeout=900)
    mesh_obj = os.path.join(mica_out, 'mesh.obj')
    assert os.path.exists(mesh_obj), 'MICA mesh.obj missing'

    s1_json, s2_json = _adapter_stage(run_dir, ad_out)

    # ---- 4. validate ----
    d = json.load(open(s2_json))
    verts = d.get('vertices', [])
    assert len(verts) == 700, 'stage2 vertices != 700 (got %d)' % len(verts)
    log('stage2_ea1.json: 700 verts OK (disp_max=%s)' % d.get('disp_max'))

    return {'mica_dir': mica_out, 'adapter_dir': ad_out,
            'stage2_ea1': s2_json, 'stage1': s1_json, 'mesh_obj': os.path.join(mica_out, 'mesh.obj')}


def _adapter_stage(run_dir, ad_out):
    """stage1 + stage2c on run_dir/mica (single or fused MICA output)."""
    mica_out = os.path.join(run_dir, 'mica')
    # ---- 2. Stage1 (path-patched copy) ----
    os.makedirs(ad_out, exist_ok=True)
    s1 = read_text(os.path.join(SCRIPTS, 'adapter_stage1.py'))
    s1 = s1.replace(r"MESH_DIR = r'C:\FL26_Mod\face_benchmark\outputs\mica\test01_front'",
                    'MESH_DIR = %r' % mica_out)
    s1 = s1.replace("OUT = os.path.join(BASE, 'adapter', 'stage1_alignment.json')",
                    'OUT = %r' % os.path.join(ad_out, 'stage1_alignment.json'))
    s1p = os.path.join(ad_out, 'adapter_stage1_run.py')
    write_text(s1p, s1)
    run_step([sys.executable.replace('python.exe', 'python.exe'), s1p], 'STAGE1',
             timeout=600)
    s1_json = os.path.join(ad_out, 'stage1_alignment.json')
    assert os.path.exists(s1_json), 'stage1 json missing'

    # ---- 3. Stage2c (path-patched copy: stage1 out + ea1 template + output) ----
    s2 = read_text(os.path.join(SCRIPTS, 'adapter_stage2c_ea1.py'))
    s2 = s2.replace("S1 = r'C:\\FL26_Mod\\face_benchmark\\adapter\\stage1_alignment.json'",
                    'S1 = %r' % s1_json)
    s2 = s2.replace("OUTJSON = r'C:\\FL26_Mod\\face_benchmark\\adapter\\stage2_ea1.json'",
                    'OUTJSON = %r' % os.path.join(ad_out, 'stage2_ea1.json'))
    # stage2c 读 ea1 模板 + mesh.obj 的行按原样保留（绝对路径都指原始输入，只读）
    # CRITICAL: point stage2c at THIS photo's MICA mesh (else every photo gets MJ's face)
    pat = 'MESH_DIR = r' + chr(39) + '[^' + chr(39) + ']*' + chr(39)
    # lambda replacement: a str replacement would let re.sub eat backslashes
    # (repr's \ collapses to \ and  in "workace" becomes a formfeed)
    s2 = re.sub(pat, lambda m: 'MESH_DIR = %r' % mica_out, s2)
    # stage1 aligns with RIGID_CORE only: jaw/chin anchors have a known semantic
    # offset between FLAME and FL26 (stage1 header says so) - the TPS in stage2c
    # must NOT use them either, else the lower face gets dragged ~2-4cm down.
    s2 = s2.replace("shared = s1['shared']",
                    "shared = s1.get('rigid_core') or s1['shared']")
    s2p = os.path.join(ad_out, 'adapter_stage2c_run.py')
    write_text(s2p, s2)
    run_step([sys.executable, s2p], 'STAGE2C', timeout=600)
    s2_json = os.path.join(ad_out, 'stage2_ea1.json')
    assert os.path.exists(s2_json), 'stage2 json missing'
    return s1_json, s2_json


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', required=True)
    ap.add_argument('--run', required=True)
    a = ap.parse_args()
    out = chain(a.photo, a.run)
    print(json.dumps(out, indent=1))
