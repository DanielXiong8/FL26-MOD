# -*- coding: utf-8 -*-
import os, subprocess, numpy as np
from PIL import Image

BASE = r'D:/FL26_Mod/work/face_pipeline/track_user1'
STAGE2 = r'D:/FL26_Mod/work/face_pipeline/phase14a5/chain_user1clean_geo/adapter/stage2_ea1.json'
REND = r'D:/FL26_Mod/work/face_pipeline/phase14a5/mica_textured_render.py'

env = dict(os.environ, RENDER_W='1200')
for tag, bake, out in [
    ('pnp', os.path.join(BASE, 'pnp_user1/bake_pnp.png'), os.path.join(BASE, 'pnp_user1/render1200')),
    ('old', os.path.join(BASE, 'baked_1024.png'), os.path.join(BASE, 'pnp_user1/render1200_old')),
]:
    os.makedirs(out, exist_ok=True)
    r = subprocess.run(['python', REND, STAGE2, bake, out, tag], env=env,
                       capture_output=True, text=True)
    print(tag, 'exit', r.returncode)
    if r.returncode:
        print((r.stderr or r.stdout)[-600:])
        continue
    for f in os.listdir(out):
        if f.endswith('.png'):
            im = np.asarray(Image.open(os.path.join(out, f)).convert('RGB'))
            bbox = np.argwhere(im.sum(2) > 90)
            if len(bbox):
                y0, x0 = bbox.min(0); y1, x1 = bbox.max(0)
                print('   %s size=%s nonbg=%d bbox(hxw)=%dx%d' % (f, im.shape[:2], len(bbox), y1-y0, x1-x0))
            else:
                print('   %s size=%s ALL-BG' % (f, im.shape[:2]))