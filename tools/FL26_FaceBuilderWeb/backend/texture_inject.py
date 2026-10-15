# -*- coding: utf-8 -*-
"""texture_inject.py — TEXTURE-ONLY face bake injection (golden-recipe compliant).

Derived from the proven Phase 11 avatar texture-inject pattern, WITHOUT the MICA
mesh step (red line: TEXTURE-ONLY NO MICA for new photos). Reads the avatar bundle
from the built APK, replaces face_eastAsia_new1 texture with the selected
candidate's baked.png, repacks the APK (zipalign+sign NOT done here — caller does).
"""
import os, shutil, zipfile
import UnityPy
from PIL import Image

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
TEX_NAME = 'face_eastAsia_new1'   # b1=14 slot (device-proven)
# V1.1: base APK carries the NEUTRAL original avatar (no MJ MICA mesh), so a photo
# bake lands on a clean head shape -> resembles the NEW person, not Ma Jiantao.


def log(msg):
    print('[texinject] %s' % msg, flush=True)


def run(apk_path, bake_png, workdir, slot_b1=14):
    """Returns (apk_path, sha256); APK updated in place with new avatar bundle."""
    import hashlib
    av_dir = os.path.join(workdir, 'avatar_work')
    os.makedirs(av_dir, exist_ok=True)
    av_src = os.path.join(av_dir, 'avatar_src.unity3d')
    av_dst = os.path.join(av_dir, 'avatar_mod.unity3d')
    with zipfile.ZipFile(apk_path) as z:
        with open(av_src, 'wb') as f:
            f.write(z.read('assets/bundles/avatar.unity3d'))
    shutil.copyfile(av_src, av_dst)

    env = UnityPy.load(av_dst)
    tex_done = False
    # TWO assets are named face_eastAsia_new1 (men's + women's atlases); the men's
    # is the one the game actually textures for our players. Match by container path.
    # device-probe mapping (B10-B15 readout): default-head players take the
    # slot face_eastAsia_new{b1-9}; b1 comes from Players.b1 AND PA app[1].
    slot_new = int(slot_b1) - 9
    assert 1 <= slot_new <= 6, 'slot_b1 must be 10-15'
    MEN_TEX_PATH = 'assets/models/player2021/textures/face/face_eastasia_new%d.png' % slot_new
    tex_obj = None
    for pth, obj in env.container.items():
        if obj.type.name == 'Texture2D' and pth.lower().endswith(MEN_TEX_PATH.lower()):
            tex_obj = obj
            log('target (container): %s' % pth)
            break
    if tex_obj is None:
        # fallback: first non-female path match, by name
        obj_path = {}
        for pth, obj in env.container.items():
            if obj.type.name == 'Texture2D' and TEX_NAME.lower() in pth.lower() and '/female/' not in pth.lower():
                obj_path[pth] = obj
        tex_obj = next(iter(obj_path.values())) if obj_path else None
    if tex_obj is not None:
        d = tex_obj.read()
        bake = Image.open(bake_png).convert('RGB')
        d.image = bake
        d.save()
        tex_done = True
        log('texture %s <- %s %s' % (TEX_NAME, os.path.basename(bake_png), bake.size))
    if not tex_done:
        raise ValueError('texture %s not found in avatar bundle' % TEX_NAME)
    with open(av_dst, 'wb') as f:
        f.write(env.file.save())

    tmp = apk_path + '.tmp2'
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
    log('APK repacked: %d bytes' % os.path.getsize(apk_path))
    return apk_path, h.hexdigest()


if __name__ == '__main__':
    import sys
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '.')
