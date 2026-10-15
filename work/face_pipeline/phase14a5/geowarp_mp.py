# -*- coding: utf-8 -*-
"""geowarp_mp.py — photo-driven DENSE face-shape warp of the EA1 700-vert template.

The person's head shape is rebuilt entirely from THEIR photo:
  1. MediaPipe FaceLandmarker -> 468 3D landmarks (x, y, z in image scale)
  2. 13 semantic anchors (uv_landmark_map <-> mediapipe idx pairs, same table the
     golden bake8 chain uses) -> 3D Umeyama similarity (both handinesses tried)
  3. per template vertex: nearest aligned-landmark displacement, confidence-weighted
  4. magnitude clamp + Laplacian smoothing on template adjacency

No MICA, no game asset sampling, no reference player. Output: stage2_ea1.json.
"""
import json, os, sys
import numpy as np

UV_DIR = os.path.join(os.environ.get('FL26_PROJECT_ROOT', r'D:\FL26_Mod'),
                      'work', 'face_pipeline', 'uv')
TASK = os.path.join(os.path.dirname(UV_DIR), 'face_landmarker_v2_with_blendshapes.task')

MP_PAIRS = {
    'left_eye':   [33, 133], 'right_eye':  [362, 263],
    'brow_center':[105, 334], 'nose_tip':   [1],  'nose_base':  [2],
    'lip_upper':  [0], 'lip_lower':  [17], 'mouth_left': [61], 'mouth_right':[291],
    'chin':       [152], 'cheek_left': [234], 'cheek_right':[454], 'forehead':  [10],
}
ANCHORS = list(MP_PAIRS.keys())


def run(photo, out_json, max_disp=0.008, nn_conf=0.030, smooth_iters=4, lam=0.45):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision
    img = cv2.imread(photo)
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    opts = vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=TASK),
        running_mode=vision.RunningMode.IMAGE, num_faces=1, min_face_detection_confidence=0.5)
    mpi = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with vision.FaceLandmarker.create_from_options(opts) as l:
        r = l.detect(mpi)
    assert r.face_landmarks, 'no face detected in ' + photo
    L = np.array([[p.x * w, p.y * h, p.z * w] for p in r.face_landmarks[0]], np.float64)
    print('mp landmarks:', L.shape)

    tv = np.asarray(json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))['vertices'], np.float64)
    mesh = json.load(open(os.path.join(UV_DIR, 'mesh_ea1.json')))
    tris = np.asarray(mesh['triangles'])[:, :, 0]
    uv = np.asarray(mesh['uv'], np.float64)
    lm = json.load(open(os.path.join(UV_DIR, 'uv_landmark_map.json')))['landmarks']

    def umeyama(src, dst):
        mu_s, mu_d = src.mean(0), dst.mean(0)
        sc, dc = src - mu_s, dst - mu_d
        cov = dc.T @ sc / len(src)
        U, S, Vt = np.linalg.svd(cov)
        d = np.ones(3); d[-1] = np.sign(np.linalg.det(U @ Vt))
        R = U @ np.diag(d) @ Vt
        var = (sc ** 2).sum() / len(src)
        s = S.sum() / var
        t = mu_d - s * R @ mu_s
        return s, R, t

    best = None
    for flip in (False, True):
        swap = {'left_eye': 'right_eye', 'right_eye': 'left_eye',
                'mouth_left': 'mouth_right', 'mouth_right': 'mouth_left',
                'cheek_left': 'cheek_right', 'cheek_right': 'cheek_left'}
        P, Q = [], []
        for name in ANCHORS:
            qn = swap.get(name, name) if flip else name
            pt = L[MP_PAIRS[name]].mean(axis=0)
            P.append(pt); Q.append(np.asarray(lm[qn]['3d'], np.float64))
        P, Q = np.array(P), np.array(Q)
        s, R, t = umeyama(P, Q)
        res = np.linalg.norm((s * (P @ R.T) + t) - Q, axis=1).mean()
        print('flipLR=%s 3D residual %.4f m' % (flip, res))
        if best is None or res < best[0]:
            best = (res, flip, s, R, t)
    res, flip, s, R, t = best
    print('chosen flip=%s scale=%.4f residual=%.4f m' % (flip, s, res))

    from scipy.spatial import KDTree
    mp_aligned = s * (L @ R.T) + t
    tr = KDTree(mp_aligned)
    nn_d, nn_i = tr.query(tv, k=1)
    disp = mp_aligned[nn_i] - tv
    conf = np.clip(1.0 - nn_d / nn_conf, 0.0, 1.0)
    disp *= conf[:, None]
    nrm = np.linalg.norm(disp, axis=1)
    over = nrm > max_disp
    disp[over] *= (max_disp / nrm[over])[:, None]

    adj = {i: set() for i in range(len(tv))}
    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        adj[a].update((b, c)); adj[b].update((a, c)); adj[c].update((a, b))
    d = disp.copy()
    for _ in range(smooth_iters):
        d2 = d.copy()
        for i, nb in adj.items():
            d2[i] = (1 - lam) * d[i] + lam * d[list(nb)].mean(axis=0)
        d = d2

    newv = tv + d
    dn = np.linalg.norm(d, axis=1)
    print('mp-warp: disp mean %.3f mm max %.3f mm | active(>0.1mm) %d/700' % (
        dn.mean() * 1000, dn.max() * 1000, int((dn > 0.0001).sum())))
    res = {'vertices': newv.tolist(), 'triangles': tris.tolist(), 'uv': uv.tolist(),
           'source': 'ea1+mp468_geowarp',
           'disp_mean': float(dn.mean()), 'disp_max': float(dn.max()),
           'alpha_mean': float(conf.mean())}
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(res, f, indent=2)
    print('saved', out_json)
    return out_json


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
