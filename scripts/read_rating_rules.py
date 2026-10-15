# -*- coding: utf-8 -*-
"""Read rating rule tables: PlayerIngameRatingRules, UserPlayerRatingRules, PlayerSkills, position tables."""
import io, sys, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"
WANT = {"PlayerIngameRatingRules", "UserPlayerRatingRules", "PlayerSkills", "GK", "DM", "RB"}

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))
    out = []
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read(check_read=False)
        nm = getattr(d, "m_Name", "")
        if nm not in WANT:
            continue
        raw = getattr(d, "m_Script", b"")
        if isinstance(raw, str):
            raw = raw.encode("utf-8", errors="surrogateescape")
        out.append(f"=== {nm} ({len(raw):,}B) ===")
        out.append(raw[:2000].decode("utf-8", errors="replace"))
        out.append("")
    text = "\n".join(out)
    with open(r"C:\FL26_Mod\logs\rating_rules.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(f"written {len(text)} chars to logs\\rating_rules.txt")

if __name__ == "__main__":
    sys.exit(main())
