# -*- coding: utf-8 -*-
# make_bake7.py - derive quality pass from bake6: lighting transfer + feathered composite
src = open(r'C:\FL26_Mod\scripts\track_d_bake6.py', encoding='utf-8').read()

# 1) lighting transfer: shade img1 with baseline-render low-frequency luminance ratio
old = """def render_to_img1(px):
    return np.stack([rbf_x(px[...,0],px[...,1]), rbf_y(px[...,0],px[...,1])], -1)"""
new = """def render_to_img1(px):
    return np.stack([rbf_x(px[...,0],px[...,1]), rbf_y(px[...,0],px[...,1])], -1)

# lighting/shading transfer: multiply photo by low-freq luminance ratio of baseline render
g_rend = cv2.GaussianBlur(cv2.cvtColor(rend, cv2.COLOR_RGB2GRAY).astype(np.float32), (0,0), 20)
g_img1 = cv2.GaussianBlur(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float32), (0,0), 20)
ratio = (g_rend + 1) / (g_img1 + 1)
img1s = np.clip(img1.astype(np.float32) * ratio[...,None], 0, 255).astype(np.uint8)
Image.fromarray(img1s[...,::-1]).save(os.path.join(WORK,'stage2_shaded.png'))"""
assert old in src
src = src.replace(old, new)

# 2) sample shaded photo
src = src.replace("out[yy[take],xx[take]] = img1[py[valid][take], px[valid][take]][..., ::-1]",
                  "out[yy[take],xx[take]] = img1s[py[valid][take], px[valid][take]][..., ::-1]")

# 3) feathered composite at the end
old2 = """print('baked %d px (%.1f%%)' % (int(mask.sum()), mask.mean()*100))
print('mean diff vs baseline: %.1f' % np.abs(out.astype(float)-base.astype(float)).mean())"""
new2 = """alpha = cv2.GaussianBlur((mask>0).astype(np.float32), (0,0), 1.5)[...,None]
outf = base.astype(np.float32)*(1-alpha) + out.astype(np.float32)*alpha
out = np.clip(outf,0,255).astype(np.uint8)
print('baked %d px (%.1f%%)' % (int(mask.sum()), mask.mean()*100))
print('mean diff vs baseline: %.1f' % np.abs(out.astype(float)-base.astype(float)).mean())"""
assert old2 in src
src = src.replace(old2, new2)
src = src.replace("baked_ea1.png", "baked_ea2.png")
open(r'C:\FL26_Mod\scripts\track_d_bake7.py', 'w', encoding='utf-8').write(src)

src2 = open(r'C:\FL26_Mod\scripts\build_baked6_apk.py', encoding='utf-8').read()
src2 = src2.replace("baked_ea1.png", "baked_ea2.png").replace("baked6", "baked7").replace("fl26_eastasia_baked.apk","fl26_eastasia_baked2.apk")
open(r'C:\FL26_Mod\scripts\build_baked7_apk.py', 'w', encoding='utf-8').write(src2)
print('ok')
