# -*- coding: utf-8 -*-
"""1. 全局球星槽(46-80)使用人数统计（选最少人用的槽）
2. 测试 UnityPy 能否把纹理像素写回 avatar.unity3d（读改写一个副本验证）"""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy
from collections import Counter

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'
AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'

# ---- 1. 全局 byte1 使用统计 ----
env = UnityPy.load(GAMEDATA)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name == 'PlayerAppearanceTable':
            rr = d.m_Script
            assets[d.m_Name] = rr.encode('utf-8', errors='surrogateescape') if isinstance(rr, str) else bytes(rr)

pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
byte1_count = Counter()
for i in range(n):
    k, o = struct.unpack_from("<II", pa, 4 + i*8)
    b1 = pa[o+5]  # byte1
    byte1_count[b1] += 1

print("全局 byte1 使用人数（球星槽 46-80）:")
FACE_NAMES = {46:'AitNouri',47:'Ake',48:'Cherki',49:'Foden',50:'Gonzalez',51:'Gvardiol',52:'Haaland',
 53:'JeremyDoku',54:'Khusanov',55:'Kovacic',56:'MarcGuehi',57:'Marmoush',58:'Marta',59:'Mbappe',
 60:'Megan',61:'NicoOReilly',62:'Nunes',63:'Putellas',64:'Reijnders',65:'Rodri',66:'RubenDias',
 67:'Savinho',68:'Stones',69:'Trafford',70:'Virgil',71:'bellingham',72:'c_Ronaldo',73:'drogba',
 74:'max',75:'messi',76:'salah',77:'semenyo',78:'son_heung_min',79:'yaml',80:'young_messi'}
slots = []
for s in range(46, 81):
    c = byte1_count.get(s, 0)
    slots.append((s, c))
    print(f"  idx {s:3d} ({FACE_NAMES.get(s,'?'):12s}): {c} 名球员")

slots.sort(key=lambda x: x[1])
print(f"\n使用人数最少的球星槽: {slots[:10]}")

# ---- 2. 测试 UnityPy 纹理写回 ----
print("\n=== 测试 UnityPy 纹理像素写回 ===")
import shutil
test_bundle = r'C:\FL26_Mod\work\face_pipeline\uv\_avatar_test.unity3d'
shutil.copy2(AVATAR, test_bundle)

env2 = UnityPy.load(test_bundle)
found = 0
for obj in env2.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_Ake':
            img = d.image
            print(f"face_Ake 读取成功: {img.size} mode={img.mode}")
            # 尝试写回：改一个像素并保存
            px = img.convert('RGBA')
            px.putpixel((10, 10), (255, 0, 0, 255))
            try:
                d.set_image(px)
                d.save()
                print("set_image + save 成功")
                found = 1
            except Exception as e:
                print(f"set_image 失败: {e}")
                # 备选：直接改 m_ImageData
                try:
                    print(f"  m_TextureFormat={d.m_TextureFormat}")
                    print(f"  尝试直接改 stream data...")
                except Exception as e2:
                    print(f"  {e2}")
            break

if found:
    with open(test_bundle, 'wb') as f:
        f.write(env2.file.save())
    print("测试 bundle 已保存（验证写回不崩溃）")

# 清理测试文件
import os
if os.path.exists(test_bundle):
    os.remove(test_bundle)
    print("测试文件已清理")
