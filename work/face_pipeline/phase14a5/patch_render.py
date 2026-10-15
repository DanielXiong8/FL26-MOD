# -*- coding: utf-8 -*-
"""patch_render.py — fix mica_textured_render.py camera/z-test completely."""
import io, ast

p = r'D:\FL26_Mod\work\face_pipeline\phase14a5\mica_textured_render.py'
s = io.open(p, encoding='utf-8').read()

# The face points -y; camera is at -y looking +y.
# Visible triangles: normals pointing -y.
# Depth: closer = smaller y; zbuf init large; keep smallest y.

s = s.replace("zbuf = np.full((W, W), -1e9)", "zbuf = np.full((W, W), 1e18)")
s = s.replace("if nn[i, 1] <= 0.0:      # backface (camera at +y)",
              "if nn[i, 1] >= 0.0:      # cull +y-facing (back of head)")
s = s.replace("upd = zb > zbuf[yy, xx]", "upd = zb < zbuf[yy, xx]")

ast.parse(s)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('orientation fix OK')
