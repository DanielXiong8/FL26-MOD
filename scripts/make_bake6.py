# -*- coding: utf-8 -*-
# make_bake6.py - derive eastasia bake from bake5: mesh_ea1 + eastasia baseline + z-priority tear fix
src = open(r'C:\FL26_Mod\scripts\track_d_bake5.py', encoding='utf-8').read()
src = src.replace("mesh_se3.json", "mesh_ea1.json")
src = src.replace("baseline_southeuropean_new3.png", "baseline_eastasia_new1.png")
src = src.replace("baked_v5.png", "baked_ea1.png")

# tear fix: z-priority overwrite (keep most front-facing triangle per texel)
old = """    yy,xx = ys[valid].astype(int), xs[valid].astype(int)
    out[yy,xx] = img1[py[valid], px[valid]][..., ::-1]
    mask[yy,xx] = 1"""
new = """    yy,xx = ys[valid].astype(int), xs[valid].astype(int)
    nz = FN[ti,2]
    take = nz >= mask[yy,xx]
    out[yy[take],xx[take]] = img1[py[valid][take], px[valid][take]][..., ::-1]
    mask[yy[take],xx[take]] = nz"""
assert old in src
src = src.replace(old, new)
src = src.replace("mask = np.zeros((TEX,TEX), np.float32)", "mask = np.zeros((TEX,TEX), np.float32)  # stores nz priority")
open(r'C:\FL26_Mod\scripts\track_d_bake6.py', 'w', encoding='utf-8').write(src)

# build script: inject into face_eastasia_new1.png + patch gamedata (Ralla b1=22, b7=127)
src2 = open(r'C:\FL26_Mod\scripts\build_baked5_apk.py', encoding='utf-8').read()
src2 = src2.replace("face_southeuropean_new3.png", "face_eastasia_new1.png")
src2 = src2.replace("baked_v5.png", "baked_ea1.png").replace("baked5", "baked6")
src2 = src2.replace("fl26_trackd_baked6.apk", "fl26_eastasia_baked.apk")
open(r'C:\FL26_Mod\scripts\build_baked6_apk.py', 'w', encoding='utf-8').write(src2)
print('ok')
