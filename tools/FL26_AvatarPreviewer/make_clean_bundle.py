"""Step 9 helper: build a script-free copy of an avatar bundle for PC preview loading.

The original FL26 bundle hard-fails AssetBundle.LoadFromFile in a clean editor
("references scripts that are not compatible") because it carries 442 MonoBehaviour
/ 33 MonoScript game objects. This tool copies the source bundle (READ-ONLY) to a
preview copy under extracted/ and strips all script objects + their component
references, keeping every Mesh/Texture2D/Material/Shader/GameObject visual asset.

Run with the system Python that has UnityPy 1.25.3:
    python make_clean_bundle.py                     # original avatar bundle
    python make_clean_bundle.py <src> <dst>         # e.g. the allchina v5c mod bundle
"""
import os
import shutil
import sys

import UnityPy

SRC = sys.argv[1] if len(sys.argv) > 1 else r"D:\FL26_Mod\build\avatar.unity3d"  # READ-ONLY input
DST = sys.argv[2] if len(sys.argv) > 2 else r"D:\FL26_Mod\tools\FL26_AvatarPreviewer\extracted\avatar_clean.unity3d"

REMOVE_TYPES = {"MonoBehaviour", "MonoScript"}


def main():
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    shutil.copyfile(SRC, DST)
    env = UnityPy.load(DST)

    sf = None

    def walk(files):
        nonlocal sf
        for _name, f in files.items():
            if hasattr(f, "objects") and f.objects:
                if sf is None or len(f.objects) > len(sf.objects):
                    sf = f
            if getattr(f, "files", None):
                walk(f.files)

    walk(env.files)
    if sf is None:
        raise SystemExit("no SerializedFile found in bundle")

    objs = sf.objects
    remove_ids = {pid for pid, o in objs.items() if o.type.name in REMOVE_TYPES}
    print("objects total:", len(objs), "| removing:", len(remove_ids))
    for pid in remove_ids:
        del objs[pid]

    # The serialized-file HEADER keeps a script type table even after the objects
    # are gone; the editor validates it on LoadFromFile and hard-fails with the
    # misleading "references scripts that are not compatible" error. Clear it.
    st = getattr(sf, "script_types", None)
    if st:
        print("clearing header script_types:", len(st))
        sf.script_types = []

    # AssetBundle object: rebuild container + preload table consistently.
    # Container entries reference the preload table by (preloadIndex, preloadSize);
    # LoadAsset resolves the whole range, so ANY deleted object inside the range
    # makes LoadAsset return null. Rebuild both: drop entries pointing at removed
    # objects / missing externals, then renumber surviving ranges.
    for _pid, o in list(objs.items()):
        if o.type.name == "AssetBundle":
            d = o.read_typetree()
            old_preload = d.get("m_PreloadTable", [])
            keep = [
                i for i, p in enumerate(old_preload)
                if p.get("m_FileID", 0) == 0 and p.get("m_PathID") in objs
            ]
            index_map = {old_i: new_i for new_i, old_i in enumerate(keep)}
            new_preload = [old_preload[i] for i in keep]

            new_cont = []
            dropped_cont = 0
            for e in d.get("m_Container", []):
                path, info = e[0], e[1]
                a = info["asset"]
                if a.get("m_FileID", 0) != 0 or a.get("m_PathID") not in objs:
                    dropped_cont += 1
                    continue
                pi, ps = info["preloadIndex"], info["preloadSize"]
                rng = [index_map[i] for i in range(pi, pi + ps) if i in index_map]
                if not rng:
                    dropped_cont += 1
                    continue
                info["preloadIndex"] = rng[0]
                info["preloadSize"] = len(rng)
                new_cont.append((path, info))
            d["m_Container"] = new_cont
            d["m_PreloadTable"] = new_preload
            o.save_typetree(d)
            print(
                f"rebuilt AssetBundle: container {len(new_cont)} (dropped {dropped_cont}), "
                f"preload {len(old_preload)}->{len(new_preload)}"
            )

    # Types-table surgery by reference count: entries whose objects were all
    # removed (all 33 MonoBehaviour/114 entries) must not remain in the table,
    # otherwise the editor still treats the file as "referencing scripts".
    # Types still used by surviving objects (e.g. SpriteAtlas's hashed id) stay.
    old_types = sf.types
    usage = set(o.type_id for o in objs.values())
    keep_map = {}
    new_types = []
    for i, t in enumerate(old_types):
        if i in usage:
            keep_map[i] = len(new_types)
            new_types.append(t)
    removed_types = len(old_types) - len(new_types)
    sf.types = new_types
    remapped = 0
    for _pid, o in objs.items():
        ti = getattr(o, "type_id", None)
        if ti is None:
            continue
        if ti in keep_map:
            if keep_map[ti] != ti:
                o.type_id = keep_map[ti]
                remapped += 1
        else:
            raise SystemExit(f"object {_pid} ({o.type.name}) references removed type {ti}")
    print(f"types surgery: removed {removed_types} unreferenced type entries, remapped {remapped} objects")

    fixed = 0
    for _pid, o in list(objs.items()):
        if o.type.name != "GameObject":
            continue
        d = o.read_typetree()
        comps = d.get("m_Component", [])
        kept = [c for c in comps if c["component"].get("m_PathID") not in remove_ids]
        if len(kept) != len(comps):
            d["m_Component"] = kept
            o.save_typetree(d)
            fixed += 1
    print("gameobjects with removed components:", fixed)

    data = env.file.save(packer="lz4")
    with open(DST, "wb") as f:
        f.write(data)
    print("saved:", DST, os.path.getsize(DST), "bytes")


if __name__ == "__main__":
    main()
