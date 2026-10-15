# -*- coding: utf-8 -*-
"""preview.py - game-equivalent face preview via the PROVEN Step10 DashboardRender.

Why DashboardRender: its front/45L/45R/side renders were user-verified correct in
Phase 12. Reuses it unchanged: writes the candidate bake into a COPY of the clean
original avatar bundle (as face_eastAsia_new1 texture - the b1=14 slot), then runs
the existing dashboard render job. Render lock serializes runs.
"""
import hashlib, json, os, shutil, subprocess, time
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
UNITY = r'D:\Unity\Editor-2020.3.49f1\Editor\Unity.exe'
PROJECT = os.path.join(ROOT, 'tools', 'FL26_AvatarPreviewer')
BUNDLE = os.path.join(ROOT, 'tools', 'FL26_AvatarPreviewer', 'extracted', 'avatar_orig_clean.unity3d')
WEB = os.path.join(ROOT, 'tools', 'FL26_FaceBuilderWeb')
CACHE_DIR = os.path.join(WEB, 'static', 'previews')
TEX_NAME = 'face_eastAsia_new1'
MESH_NAME = 'face_EastAsia_new1'
EA1_JSON = os.path.join(ROOT, 'work', 'face_pipeline', 'uv', 'mesh_ea1.json')


def ea1_vertices():
    import numpy as np
    return np.array(json.load(open(EA1_JSON))['vertices'], np.float64)
LOCK = os.path.join(WEB, 'render.lock')


def _acquire(timeout=3600):
    t0 = time.time()
    while os.path.exists(LOCK):
        if time.time() - t0 > timeout:
            os.remove(LOCK)
            break
        time.sleep(2)
    with open(LOCK, 'w') as f:
        f.write(str(os.getpid()))


def _release():
    if os.path.exists(LOCK):
        os.remove(LOCK)


def log(msg):
    print('[preview] %s' % msg, flush=True)


def bake_key(bake_png, stage2_json=None):
    h = hashlib.sha256()
    with open(bake_png, 'rb') as f:
        h.update(f.read())
    if stage2_json and os.path.exists(stage2_json):
        h.update(open(stage2_json, 'rb').read())
    return h.hexdigest()[:16]


def _pack(run_dir):
    p = run_dir.replace(chr(92), '/')
    return {'front': '/api/file/%s/dash_front.png' % p,
            '45L': '/api/file/%s/dash_45L.png' % p,
            '45R': '/api/file/%s/dash_45R.png' % p,
            'side': '/api/file/%s/dash_side.png' % p}


def render(bake_png, iris=None, stage2_json=None):
    """Renders ONE game-equivalent head preview set.
    stage2_json: personalized 700-vert mesh (mm) -> injected into the bundle copy
    so the preview shows the PERSONALIZED geometry, not the neutral head."""
    key = bake_key(bake_png, stage2_json)
    out_dir = os.path.join(CACHE_DIR, key)
    if os.path.exists(os.path.join(out_dir, 'render_done.json')):
        log('cache hit: %s' % key)
        return _pack(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # 1) bundle copy: personalized mesh verts + candidate bake texture
    bundle = os.path.join(out_dir, 'avatar_preview.unity3d')
    shutil.copyfile(BUNDLE, bundle)
    env = UnityPy.load(bundle)
    import numpy as np
    # NOTE: the bundle has TWO 'face_eastAsia_new1' textures (men + women atlases).
    # Matching by m_Name alone can hit the WOMEN's slot while the men's head model
    # still shows the default face. Target the MEN's container path explicitly.
    MEN_TEX_PATH = 'assets/models/player2021/textures/face/face_eastasia_new1.png'
    tex_by_path = {}
    mesh_by_path = {}
    for pth, o in env.container.items():
        if '/female/' in pth.lower():
            continue
        if o.type.name == 'Texture2D' and 'face_eastasia_new1' in pth.lower():
            tex_by_path[pth] = o
        if o.type.name == 'Mesh' and 'face_eastasia_new1' in pth.lower():
            mesh_by_path[pth] = o
    tex_obj = next((o for pth, o in tex_by_path.items()
                    if pth.lower().endswith(MEN_TEX_PATH.lower())), None)
    if tex_obj is None and tex_by_path:
        tex_obj = list(tex_by_path.values())[0]
    if tex_obj is None:
        raise ValueError('no men face_eastasia_new1 texture found in bundle')
    tex_path_used = [p for p, o in tex_by_path.items() if o is tex_obj][0]
    log('men tex target: %s' % tex_path_used)
    mesh_obj_t = next((o for pth, o in mesh_by_path.items()
                       if MESH_NAME.lower() in pth.lower()), None)
    if mesh_obj_t is None:
        for o in env.objects:
            if o.type.name == 'Mesh':
                d = o.read()
                if d.m_Name == MESH_NAME:
                    mesh_obj_t = o
                    break

    mesh_done = tex_done = False
    targets = []
    if mesh_obj_t is not None and stage2_json and os.path.exists(stage2_json):
        targets.append(('mesh', mesh_obj_t))
    targets.append(('tex', tex_obj))
    for kind, obj in targets:
        if kind == 'mesh' and not mesh_done:
            tree = obj.read_typetree()
            vd = tree['m_VertexData']
            nvert = vd['m_VertexCount']
            ch0 = vd['m_Channels'][0]
            stride = 0
            for ch in vd['m_Channels']:
                if ch['stream'] == 0:
                    stride = max(stride, ch['offset'] + ch['dimension'] * 4)
            data = bytearray(bytes(vd['m_DataSize']))
            fl = np.frombuffer(bytes(data), np.float32)
            pos_all = fl.reshape(-1, stride // 4)[:, ch0['offset']//4:ch0['offset']//4+3]
            d_chk = np.abs(pos_all[:nvert] * np.array([-1.0, 1.0, 1.0]) - ea1_vertices()).max()
            log('parse-vs-ea1 diff %.4f (personalized inject follows)' % d_chk)
            adapt = np.array(json.load(open(stage2_json))['vertices'], np.float64)
            adapt_g = adapt * np.array([-1.0, 1.0, 1.0])
            for i in range(nvert):
                o = i * stride
                data[o:o+12] = adapt_g[i].astype('<f4').tobytes()
            vd['m_DataSize'] = bytes(data)
            tree['m_VertexData'] = vd
            obj.save_typetree(tree)
            mesh_done = True
            log('personalized mesh injected (700 verts)')
        elif kind == 'tex' and not tex_done:
            from PIL import Image
            d = obj.read()
            d.image = Image.open(bake_png).convert('RGB')
            d.save()
            tex_done = True
            log('bake injected (men slot, %dx%d)' % (d.image.width, d.image.height))
    if not tex_done:
        raise ValueError('bake injection failed')
    with open(bundle, 'wb') as f:
        f.write(env.file.save())

    # 2) proven dashboard render job (correct orientation, user-verified in Phase 12)
    job = {'bundlePath': bundle.replace(chr(92), '/'),
           'outDir': out_dir.replace(chr(92), '/'),
           'faceAssetName': 'face_EastAsia_new1',
           # full asset path: two assets share this name (men/women); bare name
           # LoadAsset may resolve to the women's (never-injected) texture
           'textureObjectName': tex_path_used}
    job_path = os.path.join(out_dir, 'job.json')
    with open(job_path, 'w') as f:
        json.dump(job, f)

    env2 = dict(os.environ)
    env2['DASHBOARD_JOB'] = job_path
    _acquire()
    try:
        temp_dir = os.path.join(PROJECT, 'Temp')
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        lib = os.path.join(PROJECT, 'Library')
        for f in ('ArtifactDB', 'ArtifactDB-lock', 'SourceAssetDB', 'SourceAssetDB-lock'):
            fp = os.path.join(lib, f)
            if os.path.exists(fp):
                os.remove(fp)
        log('dashboard render starting (%s)...' % key)
        r = subprocess.run([UNITY, '-batchmode', '-projectPath', PROJECT,
                            '-executeMethod', 'FL26Previewer.EditorTools.DashboardRender.Run',
                            '-logFile', os.path.join(out_dir, 'unity.log')],
                           capture_output=True, text=True, timeout=2400, env=env2)
    finally:
        temp_dir2 = os.path.join(PROJECT, 'Temp')
        if os.path.exists(temp_dir2):
            shutil.rmtree(temp_dir2, ignore_errors=True)
        _release()
    if not os.path.exists(os.path.join(out_dir, 'render_done.json')):
        raise RuntimeError('preview failed (exit %s) - see %s/unity.log' % (r.returncode, out_dir))
    log('render done: %s' % key)
    return _pack(out_dir)


if __name__ == '__main__':
    import sys
    print(json.dumps(render(sys.argv[1]), indent=1))
