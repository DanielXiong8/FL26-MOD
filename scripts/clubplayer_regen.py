# -*- coding: utf-8 -*-
"""Regenerate clubplayer_registry.csv grouped by RECORD team_id (authoritative), not header order."""
import csv, struct, sys, io, zipfile
import UnityPy

APK = r"C:\FL26_Mod\working\base.apk"
OUT = r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon\04_team\clubplayer_registry.csv"

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
    craw = load_textasset(env, "ClubPlayer")
    players = {r["player_id"]: r["name"] for r in csv.DictReader(open(r"C:\Users\Lenovo\OneDrive\Desktop\fl26mod\recon\03_player\player_registry_candidates.csv", encoding="utf-8-sig"))}

    tcnt = struct.unpack_from("<I", craw, 0)[0]
    total = sum(struct.unpack_from("<I", craw, 4 + i*8 + 4)[0] for i in range(tcnt))
    off = 4 + tcnt * 8
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["team_id", "slot_index", "player_id", "player_name", "jersey", "role_byte13", "bytes9_12_hex", "bytes14_16_hex", "raw_hex"])
        cur_tid, slot = None, 0
        for i in range(total):
            rec = craw[off:off+17]; off += 17
            tid, pid = struct.unpack_from("<II", rec, 0)
            if tid != cur_tid:
                cur_tid, slot = tid, 0
            w.writerow([tid, slot, pid, players.get(str(pid), "?"), rec[8], rec[13],
                        rec[9:13].hex(), rec[14:17].hex(), rec.hex()])
            slot += 1
    print(f"regenerated {OUT}: {total} records, grouped by record.team_id")

if __name__ == "__main__":
    sys.exit(main())
