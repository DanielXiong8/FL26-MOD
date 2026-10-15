# -*- coding: utf-8 -*-
# make_magenta_variant.py - derive magenta diagnostic bake + build script from bake3/build3
src = open(r'C:\FL26_Mod\scripts\track_d_bake3.py', encoding='utf-8').read()
src = src.replace("print(\"baked %d px (%.1f%%)\" % (int(mask.sum()), mask.mean()*100))",
                  "out[mask>0]=[255,0,255]\nprint(\"baked %d px (%.1f%%)\" % (int(mask.sum()), mask.mean()*100))")
src = src.replace('baked_v3.png', 'baked_v4_magenta.png')
open(r'C:\FL26_Mod\scripts\track_d_bake4_magenta.py', 'w', encoding='utf-8').write(src)

src2 = open(r'C:\FL26_Mod\scripts\build_baked3_apk.py', encoding='utf-8').read()
src2 = src2.replace('baked_v3.png', 'baked_v4_magenta.png').replace('baked3', 'baked4m')
open(r'C:\FL26_Mod\scripts\build_baked4m_apk.py', 'w', encoding='utf-8').write(src2)
print('scripts ok')
