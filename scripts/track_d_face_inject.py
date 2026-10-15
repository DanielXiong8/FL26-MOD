# track_d_face_inject.py — Step 8 Track D: custom face texture injection
# 1) export baseline face_southeuropean_new3 texture
# 2) create modified texture (visible marker grid) via PIL
# 3) write back into avatar.unity3d -> build/avatar_trackd.unity3d
# Usage: python track_d_face_inject.py export|inject
import sys, os
import UnityPy

SRC = r"C:\FL26_Mod\build\avatar.unity3d"
OUT = r"C:\FL26_Mod\build\avatar_trackd.unity3d"
WORK = r"C:\FL26_Mod\work\face_pipeline\track_d"
TARGET = "assets/models/player2021/textures/face/face_southeuropean_new3.png"
os.makedirs(WORK, exist_ok=True)

def load_target():
    env = UnityPy.load(SRC)
    obj = env.container[TARGET]
    tex = obj.read()
    return env, obj, tex

mode = sys.argv[1] if len(sys.argv) > 1 else "export"

if mode == "export":
    env, obj, tex = load_target()
    img = tex.image
    base = os.path.join(WORK, "baseline_southeuropean_new3.png")
    img.save(base)
    print("EXPORTED", img.size, img.mode, "->", base)

elif mode == "inject":
    from PIL import Image, ImageDraw
    env, obj, tex = load_target()
    img = tex.image.convert("RGBA")
    w, h = img.size
    dr = ImageDraw.Draw(img)
    # Visible marker: big red X + cyan corner blocks + white border ring
    dr.line([(0,0),(w-1,h-1)], fill=(255,0,0,255), width=max(2,w//50))
    dr.line([(w-1,0),(0,h-1)], fill=(255,0,0,255), width=max(2,w//50))
    s = w//8
    dr.rectangle([0,0,s,s], fill=(0,255,255,255))
    dr.rectangle([w-s,0,w,s], fill=(0,255,255,255))
    dr.rectangle([0,h-s,s,h], fill=(0,255,255,255))
    dr.rectangle([w-s,h-s,w,h], fill=(0,255,255,255))
    dr.rectangle([w//8,h//8,w-w//8,h-h//8], outline=(255,255,255,255), width=max(2,w//100))
    mod = os.path.join(WORK, "modified_southeuropean_new3.png")
    img.save(mod)
    tex.set_image(img)
    tex.save()
    saved = env.file.save(packer="original")
    with open(OUT, "wb") as f:
        f.write(saved)
    print("INJECTED ->", OUT, os.path.getsize(OUT), "bytes; src =", os.path.getsize(SRC))
    # immediate reload verification
    env2 = UnityPy.load(OUT)
    tex2 = env2.container[TARGET].read()
    p = tex2.image.convert("RGB")
    print("VERIFY corner:", p.getpixel((2, 2)), "center:", p.getpixel((256, 256)))
