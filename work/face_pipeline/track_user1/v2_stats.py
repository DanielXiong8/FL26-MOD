import numpy as np, os
from PIL import Image
BASE = r'D:/FL26_Mod/work/face_pipeline/track_user1'
for tag, rel in [('pnp_front','pnp_user1/v2render/v2_front.png'),('pnp_34l','pnp_user1/v2render/v2_3_4_left.png'),('old_front','pnp_user1/v2render_old/v2_front.png'),('photo','user1_tight.jpg')]:
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        print('MISSING', rel); continue
    im = np.asarray(Image.open(p).convert('RGB')).reshape(-1,3)
    nonbg = (np.abs(im.astype(int) - np.array([18,18,18])).sum(1) > 30)
    skin = ((im[:,0]>90) & (im[:,0]>im[:,1]) & (im[:,1]>im[:,2])).mean()
    print('%-10s nonbg=%.1f%% skin=%.1f%%' % (tag, nonbg.mean()*100, skin*100))