# -*- coding: utf-8 -*-
"""
B3/B4: Identify facial landmark UV coordinates on FL26 mesh.
Calculates 3D spatial extremes and finds corresponding UVs.
Outputs:
  work/face_pipeline/uv/uv_landmark_map.json
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OUT = r'C:\FL26_Mod\work\face_pipeline\uv'

with open(os.path.join(OUT, 'mesh_topology.json')) as f:
    topo = json.load(f)
with open(os.path.join(OUT, 'mesh_uv.json')) as f:
    uv_data = json.load(f)

verts = topo['vertices']
uvs = uv_data['uv']

# Coordinate system analysis:
# X: left/right (symmetric around 0)
# Y: up/down (chin to forehead)
# Z: front/back (+Z is face front, nose tip has max Z)

# 1. Nose tip: vertex with highest Z near center (abs(X) < 0.02)
nose_candidates = [v for v in verts if abs(v['x']) < 0.02 and v['y'] > -0.05 and v['y'] < 0.05]
nose_tip = max(nose_candidates, key=lambda v: v['z'])

# 2. Chin: lowest Y near center
chin_candidates = [v for v in verts if abs(v['x']) < 0.03]
chin = min(chin_candidates, key=lambda v: v['y'])

# 3. Forehead: highest Y near center
forehead = max([v for v in verts if abs(v['x']) < 0.03 and v['z'] > 0], key=lambda v: v['y'])

# 4. Mouth center: between nose tip and chin, high Z
mouth_candidates = [v for v in verts if abs(v['x']) < 0.01 and v['y'] > chin['y'] + 0.02 and v['y'] < nose_tip['y'] - 0.02]
mouth_center = max(mouth_candidates, key=lambda v: v['z'])

# 5. Left/Right Eyes: outer/inner eye corners
# Left side (X > 0)
left_eye_candidates = [v for v in verts if v['x'] > 0.03 and v['x'] < 0.08 and v['y'] > 0.01 and v['y'] < 0.08]
left_eye_outer = max(left_eye_candidates, key=lambda v: v['x'])
left_eye_pupil = max(left_eye_candidates, key=lambda v: v['z'])

# Right side (X < 0)
right_eye_candidates = [v for v in verts if v['x'] < -0.03 and v['x'] > -0.08 and v['y'] > 0.01 and v['y'] < 0.08]
right_eye_outer = min(right_eye_candidates, key=lambda v: v['x'])
right_eye_pupil = max(right_eye_candidates, key=lambda v: v['z'])

landmarks = {
    "nose_tip": {"v_idx": nose_tip['index'], "3d": [nose_tip['x'], nose_tip['y'], nose_tip['z']], "uv": [uvs[nose_tip['index']]['u'], uvs[nose_tip['index']]['v']]},
    "chin": {"v_idx": chin['index'], "3d": [chin['x'], chin['y'], chin['z']], "uv": [uvs[chin['index']]['u'], uvs[chin['index']]['v']]},
    "forehead": {"v_idx": forehead['index'], "3d": [forehead['x'], forehead['y'], forehead['z']], "uv": [uvs[forehead['index']]['u'], uvs[forehead['index']]['v']]},
    "mouth_center": {"v_idx": mouth_center['index'], "3d": [mouth_center['x'], mouth_center['y'], mouth_center['z']], "uv": [uvs[mouth_center['index']]['u'], uvs[mouth_center['index']]['v']]},
    "left_eye": {"v_idx": left_eye_pupil['index'], "3d": [left_eye_pupil['x'], left_eye_pupil['y'], left_eye_pupil['z']], "uv": [uvs[left_eye_pupil['index']]['u'], uvs[left_eye_pupil['index']]['v']]},
    "right_eye": {"v_idx": right_eye_pupil['index'], "3d": [right_eye_pupil['x'], right_eye_pupil['y'], right_eye_pupil['z']], "uv": [uvs[right_eye_pupil['index']]['u'], uvs[right_eye_pupil['index']]['v']]},
}

print("Facial Landmarks Mapped to FL26 UV:")
for name, d in landmarks.items():
    print(f"  {name:15s}: 3D=[{d['3d'][0]:.3f}, {d['3d'][1]:.3f}, {d['3d'][2]:.3f}] -> UV=({d['uv'][0]:.4f}, {d['uv'][1]:.4f})")

with open(os.path.join(OUT, 'uv_landmark_map.json'), 'w') as f:
    json.dump(landmarks, f, indent=2)
print("Saved uv_landmark_map.json")
