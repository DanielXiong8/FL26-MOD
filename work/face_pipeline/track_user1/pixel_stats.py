# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
import os

BASE = r'D:/FL26_Mod/work/face_pipeline/track_user1'
for tag, rel in [
    ('pnp_front', 'pnp_user1/render1200/mica_skin_front.png'),
    ('pnp_34l',   'pnp_user1/render1200/mica_skin_3_4_left.png'),
    ('old_front', 'pnp_user1/render1200_old/mica_skin_front.png'),
    ('photo',     'user1_tight.jpg'),
]:
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        print('%-12s MISSING %s' % (tag, rel))
        continue
    im = np.asarray(Image.open(p).convert('RGB'))
    h, w, _ = im.shape
    flat = im.reshape(-1, 3)
    from collections import Counter
    cnt = Counter(map(tuple, flat[::7]))
    bg = cnt.most_common(1)[0][0]
    nonbg = (np.abs(flat.astype(int) - np.array(bg)).sum(1) > 40)
    skincol = ((flat[:, 0] > 100) & (flat[:, 0] > flat[:, 1]) & (flat[:, 1] > flat[:, 2])).mean()
    print('%-12s %dx%d bg=%s nonbg=%.1f%% skin=%.1f%%' % (
        tag, w, h, bg, nonbg.mean() * 100, skincol * 100))
    if nonbg.any():
        px = flat[nonbg]
        print('            painted RGB mean=(%d,%d,%d) span_r=%d' % (
            int(px[:, 0].mean()), int(px[:, 1].mean()), int(px[:, 2].mean()),
            int(px[:, 0].max() - px[:, 0].min())))