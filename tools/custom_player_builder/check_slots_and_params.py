# -*- coding: utf-8 -*-
"""检查球星纹理槽（46-80）哪些安全可替换（London Red 原版球员未占用）。
同时提取 face_southeuropean_new3 纹理参数。"""
import sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import UnityPy

GAMEDATA = r'C:\FL26_Mod\build\gamedata.unity3d'
AVATAR = r'C:\FL26_Mod\build\avatar.unity3d'

# ---- 1. London Red 球员 byte1 值 ----
env = UnityPy.load(GAMEDATA)
assets = {}
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        d = obj.read(check_read=False)
        if d.m_Name in ('Players', 'ClubPlayer', 'PlayerAppearanceTable'):
            rr = d.m_Script
            assets[d.m_Name] = rr.encode('utf-8', errors='surrogateescape') if isinstance(rr, str) else bytes(rr)

raw = assets['ClubPlayer']
n1 = struct.unpack_from("<I", raw, 0)[0]
sec2 = []
off = 4 + n1*8
while off + 17 <= len(raw):
    tid, pid, f1, f2 = struct.unpack_from("<IIII", raw, off)
    sec2.append((tid, pid, f1, f2, raw[off+16]))
    off += 17
team20030 = [r for r in sec2 if r[0] == 20030]
print(f"London Red (20030) 原版球员: {len(team20030)}")
lr_pids = [r[1] for r in team20030]

pa = assets['PlayerAppearanceTable']
n = struct.unpack_from("<I", pa, 0)[0]
app = {}
for i in range(n):
    k, o = struct.unpack_from("<II", pa, 4 + i*8)
    app[k] = pa[o+4:o+21]

lr_byte1 = {}
for pid in lr_pids:
    lr_byte1[pid] = app[pid][1] if pid in app else 'NO_APPEARANCE'

print("\nLondon Red 球员 byte1:")
used_b1 = set()
for pid, b1 in sorted(lr_byte1.items(), key=lambda x: x[0]):
    print(f"  pid {pid:6d}: byte1={b1}")
    if isinstance(b1, int):
        used_b1.add(b1)
print(f"\nLondon Red 用到的 byte1 值: {sorted(used_b1)}")

# ---- 2. 球星纹理槽 ----
star_indices = list(range(46, 81))
print(f"\n球星纹理槽 (46-80):")
print(f"被 London Red 占用的槽: {sorted(used_b1 & set(star_indices))}")
safe = sorted(set(star_indices) - used_b1)
print(f"安全可替换的槽: {safe}")

# 打印安全槽对应的纹理名（来自 GlobalTables idx）
FACE_NAMES = {46:'face_AitNouri',47:'face_Ake',48:'face_Cherki',49:'face_Foden',50:'face_Gonzalez',
 51:'face_Gvardiol',52:'face_Haaland',53:'face_JeremyDoku',54:'face_Khusanov',55:'face_Kovacic',
 56:'face_MarcGuehi',57:'face_Marmoush',58:'face_Marta',59:'face_Mbappe',60:'face_Megan',
 61:'face_NicoOReilly',62:'face_Nunes',63:'face_Putellas',64:'face_Reijnders',65:'face_Rodri',
 66:'face_RubenDias',67:'face_Savinho',68:'face_Stones',69:'face_Trafford',70:'face_Virgil',
 71:'face_bellingham',72:'face_c_Ronaldo',73:'face_drogba',74:'face_max',75:'face_messi',
 76:'face_salah',77:'face_semenyo',78:'face_son_heung_min',79:'face_yaml',80:'face_young_messi'}
print("\n安全槽对应纹理:")
for s in safe:
    print(f"  idx {s}: {FACE_NAMES.get(s, '?')}")

# ---- 3. Ralla 纹理参数 ----
env2 = UnityPy.load(AVATAR)
for obj in env2.objects:
    if obj.type.name == 'Texture2D':
        d = obj.read(check_read=False)
        if d.m_Name == 'face_southeuropean_new3':
            print(f"\n=== face_southeuropean_new3 纹理参数 ===")
            print(f"  宽: {d.m_Width}, 高: {d.m_Height}")
            print(f"  format: {d.m_TextureFormat}")
            print(f"  mipmap 数: {d.m_MipCount}")
            print(f"  filter: {d.m_FilterMode}")
            print(f"  wrap: {d.m_WrapMode}")
            print(f"  aniso: {d.m_Aniso}, mip bias: {d.m_MipBias}")
            print(f"  color space: {d.m_ColorSpace}")
            img = d.image
            if img:
                print(f"  PIL image: {img.size} mode={img.mode}")
                img.save(r'C:\FL26_Mod\work\face_pipeline\uv\face_southeuropean_new3.png')
                print("  已保存 work/face_pipeline/uv/face_southeuropean_new3.png")
            break
