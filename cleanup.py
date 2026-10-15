# -*- coding: utf-8 -*-
"""cleanup.py - D:\FL26_Mod 空间清理（保留三大工作流完整可恢复）：
A. 捏脸管线: work/face_pipeline + tools/FL26_FaceBuilderWeb(源码/backend/frontend) + FL26_FaceDashboard + build 底包/keystore + golden 管线资产
B. 球员对齐: work/fc26_alignment + build 当前产物 + saveexport 工具源码
C. 难度补丁: work/fc26_alignment/fix_difficulty.py + player_dat_fixed.bin + saveimport_tool3.apk
删除: dist 旧探针APK / FaceBuilderWeb runs+previews / build 历史 APK+bundle / AvatarPreviewer
保留: 源码、数据、白名单内的 build 资产、android-sdk、extracted/modified/recon（逆向资料）
先 --dry 列表，--go 执行。
"""
import os, sys, shutil

ROOT = r'D:\FL26_Mod'
DRY = '--go' not in sys.argv
freed = 0

def rm(path, reason):
    global freed
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return
    size = 0
    if os.path.isdir(p):
        for r, d, fs in os.walk(p):
            for f in fs:
                try: size += os.path.getsize(os.path.join(r, f))
                except OSError: pass
        if not DRY:
            shutil.rmtree(p, ignore_errors=True)
    else:
        size = os.path.getsize(p)
        if not DRY:
            os.remove(p)
    freed += size
    print('%-8s %7.1fG %s' % ('DEL' if not DRY else 'WILL', size / 1e9, path))

# ---- 1. dist 全部旧 APK（探针/历史版本；saveexport 工具已有 keep/ 备份）----
for f in os.listdir(os.path.join(ROOT, 'dist')):
    if f.endswith(('.apk', '.idsig')):
        rm(os.path.join('dist', f), 'old apk')

# ---- 2. FaceBuilderWeb 运行产物（源码保留）----
fbw = 'tools/FL26_FaceBuilderWeb'
rm(fbw + '/runs', 'face builds workdir')
rm(fbw + '/static/previews', 'face previews')
rm(fbw + '/backend/__pycache__', 'pycache')

# ---- 3. build 历史版本（保留白名单）----
KEEP_BUILD = {
    'base_debuggable2.apk',          # 对齐底包
    'base_saveexport.apk',           # 导出工具底包（未签名原始）
    'base_saveexport_aligned.apk',
    'saveexport_sign_al.apk',        # 导出工具(签名)
    'saveimport_tool3.apk',          # 导入工具(支持player.dat)
    'fl26_pl_align.apk',             # 当前装机版
    'gamedata_pl2.unity3d',          # 当前对齐数据
    'gamedata.unity3d',              # 原始参考
    'db_survey_gamedata.unity3d',    # 对齐源参考
    'fl26_test.keystore',            # 签名密钥
    'avatar.unity3d',                # 原始头像参考
    'e2e_avatar_src.unity3d',        # golden 管线参考
    'e2e_gamedata_src.unity3d',
    '_patched_classes.dex',          # 导入工具 dex
    'db_probe_gamedata.unity3d',
}
for f in os.listdir(os.path.join(ROOT, 'build')):
    if f in KEEP_BUILD or f.endswith('.idsig'):
        continue
    rm(os.path.join('build', f), 'old build artifact')

# ---- 4. AvatarPreviewer Unity 缓存 ----
rm('tools/FL26_AvatarPreviewer/Library', 'unity cache')
rm('tools/FL26_AvatarPreviewer/extracted', 'preview extracted')

print()
print('%s 共释放 %.1f GB' % ('[DRY RUN]' if DRY else '[DONE]', freed / 1e9))
