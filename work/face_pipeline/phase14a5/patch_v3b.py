# -*- coding: utf-8 -*-
"""patch_v3b.py — line-accurate V3 wiring into app.py."""
import io, ast, re

BS = chr(92)
V3 = 'D:' + BS + 'FL26_Mod' + BS + 'work' + BS + 'face_pipeline' + BS + 'phase14a5' + BS + 'v3_shape_transfer.py'
RECON = 'D:' + BS + 'FL26_Mod' + BS + 'face_benchmark' + BS + 'envs' + BS + 'envs' + BS + 'recon' + BS + 'python.exe'
p = r'D:\FL26_Mod\tools\FL26_FaceBuilderWeb\backend\app.py'
lines = io.open(p, encoding='utf-8').read().split('\n')

# locate the candidates-preview block to replace
i0 = next(i for i, l in enumerate(lines) if l.strip().startswith('_emit(job[\'id\'], \'PREVIEW\', \'RUNNING\', \'photo skeleton'))
i1 = next(i for i, l in enumerate(lines) if i > i0 and 'geowarp_mp failed' in l)
new_block = """                        _n = len(list(Path(job['run_dir']).glob('photo_*.png')))
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'MICA fusion of %%d photos + V3 shape transfer' %% _n)
                        # V3: FUSED multi-photo MICA -> stage1/2c -> DEPTH-RAY shape
                        # transfer (full MICA surface onto EA1 topology).
                        import subprocess as _sp
                        _v3 = %r
                        _recon = %r
                        photos_all = sorted(Path(job['run_dir']).glob('photo_*.png'))
                        out = chain_geometry.chain_multi([str(q) for q in photos_all], str(geo_dir))
                        _r = _sp.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                        if _r.returncode != 0:
                            raise RuntimeError('v3 transfer failed: %%s' %% (_r.stderr or _r.stdout)[-300:])
                        _emit(job['id'], 'PREVIEW', 'RUNNING', 'geometry ready (V3)')""" % (V3, RECON)
lines[i0:i1 + 1] = new_block.split('\n')
s = '\n'.join(lines)

# BUILD fallback: append V3 run after chain_multi
old_b = """                            out = chain_geometry.chain_multi([str(p) for p in photos], str(geo_dir))
                            stage2 = out['stage2_ea1']"""
new_b = """                            out = chain_geometry.chain_multi([str(p) for p in photos], str(geo_dir))
                            import subprocess as _sp2
                            _v3 = %r
                            _recon = %r
                            _r2 = _sp2.run([_recon, _v3, str(geo_dir)], capture_output=True, text=True, timeout=900)
                            if _r2.returncode != 0:
                                raise RuntimeError('v3 transfer failed: %%s' %% (_r2.stderr or _r2.stdout)[-300:])
                            stage2 = out['stage2_ea1']""" % (V3, RECON)
assert old_b in s, 'build fallback not found'
s = s.replace(old_b, new_b)
ast.parse(s)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('V3 wired OK')
