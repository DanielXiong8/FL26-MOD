# -*- coding: utf-8 -*-
"""Resolve what in-game 'Fulham' actually maps to, via strings/ui_string tables."""
import io, csv, sys, zipfile
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

def main():
    with zipfile.ZipFile(APK) as zf:
        data = zf.read("assets/bundles/gamedata.unity3d")
    env = UnityPy.load(io.BytesIO(data))

    strings = load_textasset(env, "strings").decode("utf-8-sig", errors="replace")
    ui_string = load_textasset(env, "ui_string").decode("utf-8-sig", errors="replace")

    out = []
    out.append("=== strings rows containing 'Fulham' ===")
    for line in strings.splitlines():
        if "fulham" in line.lower():
            out.append("  " + line[:160])
    out.append("=== ui_string rows containing 'Fulham' ===")
    for line in ui_string.splitlines():
        if "fulham" in line.lower():
            out.append("  " + line[:160])

    # Teams CSV: any row whose name/realname mentions fulham
    teams = load_textasset(env, "Teams").decode("utf-8-sig", errors="replace")
    out.append("=== Teams rows containing 'fulham' ===")
    for line in teams.splitlines():
        if "fulham" in line.lower():
            out.append("  " + line[:200])
    with open(r"C:\FL26_Mod\logs\fulham_resolution.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"written {len(out)} lines to logs\\fulham_resolution.txt")

if __name__ == "__main__":
    sys.exit(main())
