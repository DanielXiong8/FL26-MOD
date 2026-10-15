# -*- coding: utf-8 -*-
"""patch_v3.py — wire V3 (fused MICA + depth-ray transfer) into app.py paths."""
import io, ast

BS = chr(92)
GMP = 'D:' + BS + 'FL26_Mod' + BS + 'work' + BS + 'face_pipeline' + BS + 'phase14a5' + BS + 'v3_shape_transfer.py'
RECON = 'D:' + BS + 'FL26_Mod' + BS + 'face_benchmark' + BS + 'envs' + BS + 'envs' + BS + 'recon' + BS + 'python.exe'
p = r'D:\FL26_Mod\tools\FL26_FaceBuilderWeb\backend\app.py'
s = io.open(p, encoding='utf-8').read()

# ---- 1) candidates PREVIEW: mp-skeleton -> fused MICA + V3 ----
old1 = """                    use_geo = (job.get('payload') or {}).get('geometry') == 'on'
                    if use_geo and not stage2.exists():
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'photo skeleton (MediaPipe ~15s)')
                        # DENSE PHOTO SKELETON: 468 3D landmarks -> per-vertex
                        # displacement on the EA1 template. Photo-only, no MICA,
                        # no reference player. Runs in the recon env (mediapipe).
                        import subprocess as _sp
                        _gmp = %r
                        _recon = %r
                        _r = _sp.run([_recon, _gmp, str(Path(job['run_dir']) / 'photo_0.png'), str(stage2)],
                                     capture_output=True, text=True, timeout=300)
                        if _r.returncode != 0:
                            raise RuntimeError('geowarp_mp failed: %%s' %% (_r.stderr or _r.stdout)[-300:])""" % (GMP, RECON)
new1 = """                    use_geo = (job.get('payload') or {}).get('geometry') == 'on'
                    if use_geo and not stage2.exists():
                        _n = len(list(Path(job['run_dir']).glob('photo_*.png')))
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'MICA fusion of %%d photos + V3 shape transfer' %% _n)
                        # V3: FUSED multi-photo MICA -> stage1/2c -> DEPTH-RAY
                        # shape transfer (full MICA surface onto EA1 topology).
                        import subprocess as _sp
                        _v3 = %r
                        _recon = %r
                        photos_all = sorted(Path(job['run_dir']).glob('photo_*.png'))
                        out = chain_geometry.chain_multi([str(q) for q in photos_all], str(geo_dir))
                        _r = _sp.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                        if _r.returncode != 0:
                            raise RuntimeError('v3 transfer failed: %%s' %% (_r.stderr or _r.stdout)[-300:])
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'geometry ready (V3)')""" % (GMP, RECON)
assert old1 in s, 'candidates preview block not found'
s = s.replace(old1, new1)

# ---- 2) BUILD fallback: chain_multi + V3 ----
old2 = """                        if run_dir_cand is not None:
                            photos = sorted(run_dir_cand.glob('photo_*.png'))
                            if not photos:
                                raise RuntimeError('geometry=on but no source photos found')
                            _emit(jid, 'APK', 'RUNNING', 'MICA fusion of %d photos (~2 min)' % len(photos))
                            out = chain_geometry.chain_multi([str(p) for p in photos], str(geo_dir))
                            stage2 = out['stage2_ea1']"""
new2 = """                        if run_dir_cand is not None:
                            photos = sorted(run_dir_cand.glob('photo_*.png'))
                            if not photos:
                                raise RuntimeError('geometry=on but no source photos found')
                            _emit(jid, 'APK', 'RUNNING', 'MICA fusion of %%d photos + V3 transfer' %% len(photos))
                            out = chain_geometry.chain_multi([str(p) for p in photos], str(geo_dir))
                            import subprocess as _sp2
                            _v3 = %r
                            _recon = %r
                            _r2 = _sp2.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                            if _r2.returncode != 0:
                                raise RuntimeError('v3 transfer failed: %%s' %% (_r2.stderr or _r2.stdout)[-300:])
                            stage2 = out['stage2_ea1']""" % (GMP, RECON)
assert old2 in s, 'build fallback block not found'
s = s.replace(old2, new2)

ast.parse(s)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('V3 wired into both paths OK')
