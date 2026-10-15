# -*- coding: utf-8 -*-
# make_bake5_build.py - derive build script for baked_v5
src2 = open(r'C:\FL26_Mod\scripts\build_baked3_apk.py', encoding='utf-8').read()
src2 = src2.replace('baked_v3.png', 'baked_v5.png').replace('baked3', 'baked5')
open(r'C:\FL26_Mod\scripts\build_baked5_apk.py', 'w', encoding='utf-8').write(src2)
print('ok')
