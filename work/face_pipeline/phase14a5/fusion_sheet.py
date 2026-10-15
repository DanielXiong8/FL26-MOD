# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw
B = r'D:\FL26_Mod\face_benchmark\outputs\mica\reg4_fused'
labels = ['fused (3 photos)', 'photo reg4_01', 'photo reg4_02', 'photo reg4_03']
dirs = ['fused_input', 'per_photo_01', 'per_photo_02', 'per_photo_03']
W = 420
imgs = []
for d in dirs:
    p = B + '\\' + d + r'\mica_views\mica_front.png'
    im = Image.open(p).convert('RGB')
    im.thumbnail((W, W)); imgs.append(im)
H = max(i.height for i in imgs) + 40
canvas = Image.new('RGB', (W * 4 + 50, H), (18, 20, 26))
dr = ImageDraw.Draw(canvas)
for k, (im, lb) in enumerate(zip(imgs, labels)):
    x = k * (W + 12) + 8
    canvas.paste(im, (x + (W - im.width) // 2, 30))
    dr.text((x + 8, 8), lb, fill=(143, 211, 255))
out = r'D:\FL26_Mod\work\face_pipeline\regression\mica_fusion_compare.png'
canvas.save(out)
print('saved', out)
