# -*- coding: utf-8 -*-
"""Render MICA-adapted FL26 ea1 with correct UV handling.
UV x-range: -0.056 to 1.055 (exceeds 0-1 by ~5.5% on each side).
Solution: expand texture horizontally by 5.5% left/right via mirror padding,
then remap UV to [0,1] in the expanded texture.
"""
import os, json
import numpy as np
import trimesh
from PIL import Image as PILImage, ImageOps

ADAPT = r'D:\FL26_Mod\face_benchmark\adapter\stage2_ea1.json'
EA1   = r'D:\FL26_Mod\work\face_pipeline\uv\mesh_ea1.json'
TEXCAND = [r'C:/FL26_Mod/work/face_pipeline/track_d/baked_ea3.png',
            r'C:/FL26_Mod/work/face_pipeline/track_d/baked_111.png',
            r'C:/FL26_Mod/work/face_pipeline/track_d/baked_ea1.png']
OUT = r'D:\FL26_Mod\face_benchmark\adapter\mica_mjt1_textured_front.png'

def main():
    ad = json.load(open(ADAPT))
    ea = json.load(open(EA1))
    verts = np.asarray(ad['vertices'], np.float64)
    tris = np.asarray(ea['triangles'])[:, :, 0]
    uv = np.asarray(ea['uv'], np.float64)
    print('UV range:', uv.min(axis=0), uv.max(axis=0))
    # UV x runs -0.056 to 1.055 -> need 5.5% padding left+right
    pad_left = abs(uv[:,0].min())  # ~0.056
    pad_right = uv[:,0].max() - 1.0  # ~0.055
    x_scale = 1.0 + pad_left + pad_right  # ~1.111
    uv_remap = uv.copy()
    uv_remap[:, 0] = (uv[:,0] + pad_left) / x_scale
    uv_remap[:, 1] = 1.0 - uv_remap[:, 1]  # v flip
    uv_remap = np.clip(uv_remap, 0, 1)
    print('remapped UV range:', uv_remap.min(axis=0), uv_remap.max(axis=0))
    # Rotate FL26 -> standard render: face toward +Z, up +Y
    R = np.array([[1, 0, 0],
                  [0, 0, 1],
                  [0, -1, 0]])
    v_rot = verts @ R.T
    # Load texture and pad horizontally (mirror)
    tex_path = next((p for p in TEXCAND if os.path.exists(p)), None)
    print('tex:', tex_path)
    tex_img = PILImage.open(tex_path).convert('RGB')
    w, h = tex_img.size
    pad_px_l = int(w * pad_left)
    pad_px_r = int(w * pad_right)
    tex_pad = PILImage.new('RGB', (w + pad_px_l + pad_px_r, h))
    # mirror pad left: flip left strip
    left_strip = tex_img.crop((0, 0, pad_px_l, h)).transpose(PILImage.FLIP_LEFT_RIGHT)
    right_strip = tex_img.crop((w - pad_px_r, 0, w, h)).transpose(PILImage.FLIP_LEFT_RIGHT)
    tex_pad.paste(left_strip, (0, 0))
    tex_pad.paste(tex_img, (pad_px_l, 0))
    tex_pad.paste(right_strip, (pad_px_l + w, 0))
    tex = trimesh.visual.texture.SimpleMaterial(image=tex_pad)
    mesh = trimesh.Trimesh(vertices=v_rot, faces=tris,
                           visual=trimesh.visual.TextureVisuals(uv=uv_remap, material=tex),
                           process=False)
    scene = trimesh.Scene(mesh)
    scene.camera.resolution = (700, 700)
    png = scene.save_image()
    with open(OUT, 'wb') as fh:
        fh.write(png)
    print('saved', OUT, len(png))

if __name__ == '__main__':
    main()