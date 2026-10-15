# -*- coding: utf-8 -*-
"""
B4 v3: Corrected landmark mapping.
Key corrections:
  - Mesh is Z-up (shell/mask geometry), NOT Y-up
  - UV targets derived from TEXTURE PIXEL ANALYSIS (A-level):
      eyes  : u=0.391/0.609, v=0.734  (darkest symmetric pair)
      lips  : u=0.500,       v=0.610  (max redness zone)
      nose  : u=0.500,       v~0.68   (between eyes and lips)
  - Enforce unique vertex per landmark
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OUT = r'C:\FL26_Mod\work\face_pipeline\uv'

with open(os.path.join(OUT, 'mesh_topology.json')) as f:
    topo = json.load(f)
with open(os.path.join(OUT, 'mesh_uv.json')) as f:
    uv_data = json.load(f)

points = []
for v, u in zip(topo['vertices'], uv_data['uv']):
    points.append({'index': v['index'], 'x': v['x'], 'y': v['y'], 'z': v['z'], 'u': u['u'], 'v': u['v']})

# 3D bounding box for orientation sanity
xs = [p['x'] for p in points]; ys = [p['y'] for p in points]; zs = [p['z'] for p in points]
print(f"3D bbox: X [{min(xs):.4f}, {max(xs):.4f}]  Y [{min(ys):.4f}, {max(ys):.4f}]  Z [{min(zs):.4f}, {max(zs):.4f}]")

used = set()
def pick(name, tu, tv):
    """closest unused vertex to target uv"""
    best = None
    for p in sorted(points, key=lambda p: (p['u']-tu)**2 + (p['v']-tv)**2):
        if p['index'] not in used:
            best = p
            break
    used.add(best['index'])
    return {
        'name': name, 'v_idx': best['index'],
        'uv': [round(best['u'], 4), round(best['v'], 4)],
        'target_uv': [tu, tv],
        '3d': [round(best['x'], 4), round(best['y'], 4), round(best['z'], 4)],
        'uv_error': round(((best['u']-tu)**2 + (best['v']-tv)**2) ** 0.5, 5),
    }

landmarks = [
    # center line (top -> bottom), texture-derived targets
    pick('forehead',      0.500, 0.860),
    pick('brow_center',   0.500, 0.770),
    pick('left_eye',      0.391, 0.734),
    pick('right_eye',     0.609, 0.734),
    pick('nose_bridge',   0.500, 0.700),
    pick('nose_tip',      0.500, 0.660),
    pick('nose_base',     0.500, 0.630),
    pick('lip_upper',     0.500, 0.610),
    pick('lip_lower',     0.500, 0.580),
    pick('mouth_left',    0.440, 0.600),
    pick('mouth_right',   0.560, 0.600),
    pick('chin',          0.500, 0.450),
    pick('chin_bottom',   0.500, 0.370),
    # face outline (cheeks/jaw)
    pick('cheek_left',    0.250, 0.620),
    pick('cheek_right',   0.750, 0.620),
    pick('jaw_left',      0.330, 0.430),
    pick('jaw_right',     0.670, 0.430),
    pick('temple_left',   0.170, 0.750),
    pick('temple_right',  0.830, 0.750),
]

print("\n=== Corrected FL26 UV landmark map (texture-derived targets) ===")
ok = True
for lm in landmarks:
    flag = "OK " if lm['uv_error'] < 0.05 else "WARN"
    if lm['uv_error'] >= 0.05: ok = False
    print(f"  [{flag}] {lm['name']:13s}: UV=({lm['uv'][0]:.3f},{lm['uv'][1]:.3f}) target=({lm['target_uv'][0]:.3f},{lm['target_uv'][1]:.3f}) err={lm['uv_error']:.4f} 3D=({lm['3d'][0]:+.3f},{lm['3d'][1]:+.3f},{lm['3d'][2]:+.3f})")

# Z-up sanity: forehead z > chin z; eyes symmetric x; nose z between brow and lip
res = {lm['name']: lm for lm in landmarks}
checks = [
    ("forehead z > chin z", res['forehead']['3d'][2] > res['chin']['3d'][2]),
    ("eyes symmetric in x", abs(res['left_eye']['3d'][0] + res['right_eye']['3d'][0]) < 0.01),
    ("eyes same height z", abs(res['left_eye']['3d'][2] - res['right_eye']['3d'][2]) < 0.01),
    ("nose_tip x near 0", abs(res['nose_tip']['3d'][0]) < 0.02),
    ("eye z > lip z (vertical order)", res['left_eye']['3d'][2] > res['lip_upper']['3d'][2]),
    ("lip z > chin z", res['lip_upper']['3d'][2] > res['chin']['3d'][2]),
]
print("\n=== Geometry sanity checks (Z-up) ===")
all_pass = True
for name, passed in checks:
    print(f"  {'PASS' if passed else 'FAIL'}: {name}")
    all_pass = all_pass and passed

with open(os.path.join(OUT, 'uv_landmark_map.json'), 'w') as f:
    json.dump({
        'mesh': 'face_African_new1',
        'coordinate_system': 'Z-up (mask shell), X = left-right, Y = depth',
        'uv_targets_source': 'texture pixel analysis (eyes=dark symmetric pair, lips=redness max)',
        'landmarks': res,
        'geometry_checks_passed': all_pass,
    }, f, indent=2)
print(f"\nSaved uv_landmark_map.json ({len(landmarks)} landmarks, geometry_checks={'ALL PASS' if all_pass else 'SOME FAIL'})")
