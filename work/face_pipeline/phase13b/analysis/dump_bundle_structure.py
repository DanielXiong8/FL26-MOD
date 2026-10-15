# Phase 13B - Analysis 1: avatar bundle structure dump
# Read-only. Builds complete hierarchy: heads/hairs/beards/eyes + materials.
import json, os, sys
import UnityPy

ROOT = os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod')
BUNDLE = os.path.join(ROOT, r'build\avatar_ea3_v5.unity3d')
OUT = os.path.join(ROOT, r'work\face_pipeline\phase13b\analysis')

env = UnityPy.load(BUNDLE)
objs = list(env.objects)
by_pid = {}
for o in objs:
    by_pid[o.path_id] = o
print('objects:', len(objs))
from collections import Counter
print(Counter(o.type.name for o in objs))

# ---------- object name maps ----------
def name_of(o):
    try:
        d = o.read(check_read=False)
        return getattr(d, 'm_Name', getattr(d, 'name', ''))
    except Exception as e:
        return '<err %s>' % e

go_name = {}      # path_id -> name
for o in objs:
    if o.type.name == 'GameObject':
        go_name[o.path_id] = name_of(o)

# ---------- component index: GameObject -> {type: path_id} ----------
go_comps = {}     # go path_id -> [(type, comp path_id)]
for o in objs:
    t = o.type.name
    if t in ('Transform', 'SkinnedMeshRenderer', 'MeshRenderer', 'MeshFilter'):
        try:
            d = o.read(check_read=False)
            g = d.m_GameObject
            gid = g.path_id if hasattr(g, 'path_id') else g.m_PathID
        except Exception:
            continue
        go_comps.setdefault(gid, []).append((t, o.path_id))

def resolve(pptr):
    pid = pptr.path_id if hasattr(pptr, 'path_id') else pptr.m_PathID
    return pid

# ---------- transforms ----------
tr_data = {}      # transform path_id -> dict(go, father, children)
for o in objs:
    if o.type.name == 'Transform':
        d = o.read(check_read=False)
        father = resolve(d.m_Father) if d.m_Father else 0
        kids = [resolve(c) for c in (d.m_Children or [])]
        gid = resolve(d.m_GameObject)
        tr_data[o.path_id] = {'go': gid, 'father': father, 'kids': kids}

# transform of a GameObject
go_tr = {}
for tp, td in tr_data.items():
    go_tr[td['go']] = tp

def parent_chain(gid):
    chain = []
    tp = go_tr.get(gid)
    seen = set()
    while tp and tp not in seen:
        seen.add(tp)
        td = tr_data[tp]
        pgid = td['father'] and tr_data.get(td['father'], {}).get('go', 0)
        if not pgid:
            break
        chain.append(go_name.get(pgid, '?%d' % pgid))
        tp = go_tr.get(pgid)
    return list(reversed(chain))

def child_names(gid):
    tp = go_tr.get(gid)
    if not tp:
        return []
    return [go_name.get(tr_data[k]['go'], '?') for k in tr_data[tp]['kids']]

# ---------- renderers: GO -> (mesh, materials) ----------
go_render = {}    # go path_id -> {'mesh': name, 'mats': [names], 'smr': bool}
for o in objs:
    t = o.type.name
    if t == 'SkinnedMeshRenderer':
        d = o.read(check_read=False)
        gid = resolve(d.m_GameObject)
        mesh_pid = resolve(d.m_Mesh) if d.m_Mesh else 0
        mesh = go_name.get(0) or ''
        mesh_name = name_of(by_pid[mesh_pid]) if mesh_pid in by_pid else ('?%d' % mesh_pid)
        mats = [name_of(by_pid[resolve(m)]) if resolve(m) in by_pid else '?%d' % resolve(m) for m in (d.m_Materials or [])]
        go_render[gid] = {'mesh': mesh_name, 'mats': mats, 'smr': True}
    elif t == 'MeshFilter':
        d = o.read(check_read=False)
        gid = resolve(d.m_GameObject)
        mesh_pid = resolve(d.m_Mesh) if d.m_Mesh else 0
        mesh_name = name_of(by_pid[mesh_pid]) if mesh_pid in by_pid else ('?%d' % mesh_pid)
        e = go_render.setdefault(gid, {'mesh': None, 'mats': [], 'smr': False})
        e['mesh'] = mesh_name
    elif t == 'MeshRenderer':
        d = o.read(check_read=False)
        gid = resolve(d.m_GameObject)
        mats = [name_of(by_pid[resolve(m)]) if resolve(m) in by_pid else '?%d' % resolve(m) for m in (d.m_Materials or [])]
        e = go_render.setdefault(gid, {'mesh': None, 'mats': [], 'smr': False})
        e['mats'] = mats

# ---------- full GameObject flat dump ----------
all_gos = []
for gid, nm in sorted(go_name.items(), key=lambda kv: kv[1]):
    e = go_render.get(gid, {})
    all_gos.append({
        'name': nm,
        'path': '/'.join(parent_chain(gid) + [nm]),
        'mesh': e.get('mesh'),
        'mats': e.get('mats', []),
        'children': child_names(gid),
    })
with open(os.path.join(OUT, 'bundle_gos.json'), 'w', encoding='utf-8') as f:
    json.dump(all_gos, f, ensure_ascii=False, indent=1)
print('GO dump -> bundle_gos.json (%d)' % len(all_gos))

# ---------- heads & face meshes ----------
meshes = {}
for o in objs:
    if o.type.name == 'Mesh':
        d = o.read(check_read=False)
        try:
            vc = len(d.m_Vertices) // 3 if d.m_Vertices else None
        except Exception:
            vc = None
        meshes[o.path_id] = {'name': d.m_Name, 'verts': vc}

face_ea = sorted([m['name'] for m in meshes.values() if 'face_eastasia' in m['name'].lower() or 'face_east' in m['name'].lower()])
heads = sorted([m['name'] for m in meshes.values() if m['name'].lower().startswith('head_')])
hairs = sorted([m['name'] for m in meshes.values() if m['name'].lower().startswith('hair')])
beards_m = sorted([m['name'] for m in meshes.values() if 'beard' in m['name'].lower()])
print('face_EastAsia meshes:', face_ea)
print('head_* mesh count:', len(heads))
print('hair_* mesh count:', len(hairs))
print('beard meshes:', beards_m if beards_m else 'NONE (beard may be texture-only)')

# heads/hairs: where do they sit in hierarchy, what materials
def node_report(filter_fn):
    out = []
    for g in all_gos:
        if filter_fn(g['name']):
            out.append({'name': g['name'], 'path': g['path'], 'mesh': g['mesh'], 'mats': g['mats']})
    return out

head_nodes = node_report(lambda n: n.lower().startswith('head_') or 'face_east' in n.lower())
hair_nodes = node_report(lambda n: n.lower().startswith('hair'))
beard_nodes = node_report(lambda n: 'beard' in n.lower())
eye_nodes = node_report(lambda n: 'eye' in n.lower() or 'brow' in n.lower())
with open(os.path.join(OUT, 'bundle_heads.json'), 'w', encoding='utf-8') as f:
    json.dump({'head_nodes': head_nodes, 'hair_nodes': hair_nodes,
               'beard_nodes': beard_nodes, 'eye_nodes': eye_nodes},
              f, ensure_ascii=False, indent=1)
print('head nodes:', len(head_nodes), '| hair nodes:', len(hair_nodes),
      '| beard nodes:', len(beard_nodes), '| eye nodes:', len(eye_nodes))

# ---------- materials ----------
mats_out = {}
def tex_name(pid):
    if pid in by_pid:
        return name_of(by_pid[pid])
    return None

for o in objs:
    if o.type.name != 'Material':
        continue
    d = o.read(check_read=False)
    mn = d.m_Name
    shader = '?'
    try:
        sp = resolve(d.m_Shader)
        if sp in by_pid:
            sd = by_pid[sp].read(check_read=False)
            shader = getattr(getattr(sd, 'm_ParsedForm', sd), 'm_Name', '?')
    except Exception as e:
        shader = '<err>'
    props = {'tex': {}, 'col': {}, 'flt': {}}
    try:
        sp2 = d.m_SavedProperties
        for te in sp2.m_TexEnvs:
            key = te.m_Name if hasattr(te, 'm_Name') else te[0]
            tex = te.m_Texture if hasattr(te, 'm_Texture') else te[1].m_Texture
            pid = resolve(tex) if tex else 0
            props['tex'][key] = tex_name(pid) if pid else None
        for c in sp2.m_Colors:
            props['col'][c.m_Name if hasattr(c, 'm_Name') else c[0]] = list(c.m_Color if hasattr(c, 'm_Color') else c[1])
        for fl in sp2.m_Floats:
            props['flt'][fl.m_Name if hasattr(fl, 'm_Name') else fl[0]] = fl.m_Value if hasattr(fl, 'm_Value') else fl[1]
    except Exception as e:
        props['err'] = str(e)
    mats_out[mn] = {'shader': shader, 'props': props}

with open(os.path.join(OUT, 'bundle_materials.json'), 'w', encoding='utf-8') as f:
    json.dump(mats_out, f, ensure_ascii=False, indent=1)
print('materials dumped:', len(mats_out))
eye_mats = [k for k in mats_out if 'eye' in k.lower()]
face_mats = [k for k in mats_out if 'face' in k.lower() or 'head' in k.lower() or 'skin' in k.lower()]
print('eye materials:', eye_mats)
print('face/skin materials:', face_mats[:10])

# quick eye material detail
for k in eye_mats:
    m = mats_out[k]
    print('---', k, 'shader=', m['shader'])
    print('  tex:', json.dumps(m['props'].get('tex', {}), ensure_ascii=False))
    print('  col:', json.dumps(m['props'].get('col', {}), ensure_ascii=False)[:300])

print('DONE')
