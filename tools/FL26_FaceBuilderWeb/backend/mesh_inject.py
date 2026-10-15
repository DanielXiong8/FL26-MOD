# -*- coding: utf-8 -*-
"""mesh_inject.py — inject PERSONALIZED face geometry + bake texture into a built APK.

Reuses the DEVICE-PROVEN Phase 11 pattern (phase11_e2e_avatar_inject.py):
  avatar bundle: face_EastAsia_new1 mesh verts <- stage2_ea1.json (700, mm->m)
                 face_eastAsia_new1 texture  <- candidate bake
Mesh vertex units: stage2 json is mm; Unity mesh is m -> /1000 with X-flip
(x-flip verified by phase11: 'parse-vs-original-ea1 (x-flip)').
"""
import os, shutil, zipfile, json
import numpy as np
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
EA1 = os.path.join(ROOT, 'work', 'face_pipeline', 'uv', 'mesh_ea1.json')
MESH_NAME = 'face_EastAsia_new1'
TEX_NAME = 'face_eastAsia_new1'  # overridden per-slot in run()


def log(msg):
    print('[meshinject] %s' % msg, flush=True)


def run(apk_path, stage2_json, bake_png, workdir, slot_b1=14):
    """apk_path: built player APK (gamedata already injected).
    stage2_json: personalized 700-vert mesh (mm). bake_png: face texture.
    Returns (apk_path, sha256)."""
    import hashlib
    av_dir = os.path.join(workdir, 'avatar_work')
    os.makedirs(av_dir, exist_ok=True)
    av_src = os.path.join(av_dir, 'avatar_src.unity3d')
    av_dst = os.path.join(av_dir, 'avatar_mod.unity3d')
    with zipfile.ZipFile(apk_path) as z:
        with open(av_src, 'wb') as f:
            f.write(z.read('assets/bundles/avatar.unity3d'))
    shutil.copyfile(av_src, av_dst)

    ea1 = np.array(json.load(open(EA1))['vertices'], np.float64)
    adapt = np.array(json.load(open(stage2_json))['vertices'], np.float64)
    assert len(adapt) == len(ea1) == 700, 'vertex count mismatch: %d vs %d' % (len(adapt), len(ea1))

    env = UnityPy.load(av_dst)
    mesh_done = tex_done = False
    for obj in env.objects:
        if obj.type.name == 'Mesh':
            m = obj.read()
            if m.m_Name != MESH_NAME:
                continue
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
            # parse-convention check: game x = -ea1 x (phase11 v5c convention)
            d_chk = np.abs(pos_all[:nvert] * np.array([-1.0, 1.0, 1.0]) - ea1.astype(np.float32)).max()
            log('parse-vs-ea1 max diff = %.4f (high = MICA verts already present)' % d_chk)
            adapt_g = adapt * np.array([-1.0, 1.0, 1.0])
            for i in range(nvert):
                o = i * stride
                data[o:o+12] = adapt_g[i].astype('<f4').tobytes()
            vd['m_DataSize'] = bytes(data)
            # ---- INDEX SURGERY: degenerate the eyelid flap triangles. They are a
            # detached-UV island over the eyes sharing atlas texels with the face;
            # with a photo decal they display misaligned content over the eyes.
            # Detected self-contained: game-mesh UVs (stream1) + injected positions.
            try:
                ch1 = [c for c in vd['m_Channels'] if c['stream'] == 1 and c['dimension'] == 2][0]
                s0 = 0
                for ch in vd['m_Channels']:
                    if ch['stream'] == 0 and ch['dimension'] > 0:
                        s0 = max(s0, ch['offset'] + ch['dimension'] * 4)
                s1 = ch1['offset'] + ch1['dimension'] * 4
                uvb = np.frombuffer(bytes(vd['m_DataSize']), np.float32)
                uvall = uvb[nvert * s0 // 4:].reshape(-1, s1 // 4)[:, ch1['offset'] // 4:ch1['offset'] // 4 + 2]
                uvam = uvall[:nvert]
                trig = adapt_g.reshape(-1, 3)
                tc3 = trig[TRI_lid] if False else None
                # game index buffer (uint16), triangle k verts = idx[3k:3k+3]
                ib = np.frombuffer(bytes(tree['m_IndexBuffer']), np.uint16).reshape(-1, 3).copy()
                uv_c = uvam[ib].mean(1)                       # per-tri uv centroid (game frame)
                v3 = adapt_g[ib]                              # per-tri verts (game frame)
                tc3 = v3.mean(1)
                pL = np.array([-0.0296, -0.0808, 0.0605]); pR = np.array([0.0296, -0.0808, 0.0605])
                de = np.minimum(np.linalg.norm(tc3 - pL, axis=1), np.linalg.norm(tc3 - pR, axis=1))
                inC = (uv_c[:, 0] >= 0.363) & (uv_c[:, 0] <= 0.616) & (uv_c[:, 1] >= 0.367) & (uv_c[:, 1] <= 0.622)
                inL = (uv_c[:, 0] < 0.30) & (uv_c[:, 1] >= 0.19) & (uv_c[:, 1] <= 0.80)
                inR = (uv_c[:, 0] > 0.70) & (uv_c[:, 1] >= 0.19) & (uv_c[:, 1] <= 0.80)
                kill = np.where(((inC | inL | inR) & (de < 0.045)))[0]
                ib[kill] = 0                                   # degenerate: renders nothing
                tree['m_IndexBuffer'] = ib.astype(np.uint16).tobytes()
                log('index surgery: %d lid triangles degenerated' % len(kill))
            except Exception as _ex:
                log('index surgery skipped: %s' % _ex)
            tree['m_VertexData'] = vd
            obj.save_typetree(tree)
            mesh_done = True
            log('mesh %s verts injected (n=%d)' % (MESH_NAME, nvert))
            break
    assert mesh_done, '%s mesh not found' % MESH_NAME

    from PIL import Image
    for obj in env.objects:
        if obj.type.name == 'Texture2D':
            d = obj.read()
            tex_name = 'face_eastAsia_new%d' % (int(slot_b1) - 9)
            if d.m_Name == tex_name:
                d.image = Image.open(bake_png).convert('RGB')
                d.save()
                tex_done = True
                log('texture %s <- bake' % TEX_NAME)
                break
    if not tex_done:
        raise ValueError('%s texture not found' % TEX_NAME)

    with open(av_dst, 'wb') as f:
        f.write(env.file.save())

    tmp = apk_path + '.tmp3'
    with zipfile.ZipFile(apk_path, 'r') as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename == 'assets/bundles/avatar.unity3d':
                with open(av_dst, 'rb') as f:
                    zout.writestr(item, f.read())
            else:
                zout.writestr(item, zin.read(item.filename))
    shutil.move(tmp, apk_path)
    h = hashlib.sha256()
    with open(apk_path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return apk_path, h.hexdigest()
