# -*- coding: utf-8 -*-
"""Parse PlayerIngameRatingRules / UserPlayerRatingRules as (u32 id, float32 weights[])."""
import io, struct, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"

def load_textasset(env, want):
    for o in env.objects:
        if o.type.name == "TextAsset":
            d = o.read(check_read=False)
            if getattr(d, "m_Name", "") == want:
                raw = getattr(d, "m_Script", b"")
                if isinstance(raw, str):
                    raw = raw.encode("utf-8", errors="surrogateescape")
                return bytes(raw)
    raise KeyError(want)

def dump_floats(name, raw):
    print(f"=== {name} ({len(raw)}B) as (u32 + float32s) ===")
    n = len(raw) // 4
    vals = struct.unpack_from(f"<{n}I", raw, 0)
    floats = struct.unpack_from(f"<{n}f", raw, 0)
    # print rows: try to find record stride by u32 small-int markers
    for i in range(min(n, 40)):
        v, f = vals[i], floats[i]
        tag = ""
        if v <= 64: tag = "IDX?"
        print(f"  [{i:3d}] u32={v:<12} f32={f:>12.4f} {tag}")

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    dump_floats("PlayerIngameRatingRules", load_textasset(env, "PlayerIngameRatingRules"))
    dump_floats("UserPlayerRatingRules", load_textasset(env, "UserPlayerRatingRules"))

if __name__ == "__main__":
    sys.exit(main())
