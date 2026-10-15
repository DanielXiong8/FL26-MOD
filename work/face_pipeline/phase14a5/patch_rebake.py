# -*- coding: utf-8 -*-
"""patch_rebake.py — after V3 transfer, re-bake the photo skin ON the V3 geometry."""
import io, ast

BS = chr(92)
p = r'D:\FL26_Mod\tools\FL26_FaceBuilderWeb\backend\app.py'
s = io.open(p, encoding='utf-8').read()

old = """                            stage2 = out['stage2_ea1']
                        else:
                            raise RuntimeError('geometry=on but no candidate photos found for MICA')
                    _emit(jid, 'APK', 'RUNNING', 'mesh+texture inject')"""
new = """                            stage2 = out['stage2_ea1']
                            _emit(jid, 'APK', 'RUNNING', 're-bake skin on V3 geometry')
                            _bake8 = %r
                            _env3 = dict(os.environ)
                            _env3['BAKE_V3_JSON'] = stage2
                            _env3['PYTHONIOENCODING'] = 'utf-8'
                            _r3 = _sp2.run([_recon, _bake8, str(photos[0])],
                                           cwd=os.path.dirname(_bake8), capture_output=True,
                                           text=True, timeout=900, env=_env3)
                            if _r3.returncode != 0:
                                raise RuntimeError('v3 rebake failed: %%s' %% (_r3.stderr or _r3.stdout)[-400:])
                            bake_png = os.path.join(os.path.dirname(_bake8), 'baked_ea3.png')
                        else:
                            raise RuntimeError('geometry=on but no candidate photos found for MICA')
                    _emit(jid, 'APK', 'RUNNING', 'mesh+texture inject')""" % (
    'D:' + BS + 'FL26_Mod' + BS + 'work' + BS + 'face_pipeline' + BS + 'track_user1' + BS + 'bake8_user.py')
assert old in s, 'v3 tail block not found'
s = s.replace(old, new)
ast.parse(s)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('re-bake wired OK')
