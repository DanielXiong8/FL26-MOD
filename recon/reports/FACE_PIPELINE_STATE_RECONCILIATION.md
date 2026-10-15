# FACE_PIPELINE_STATE_RECONCILIATION.md — 脸部管线状态对账（2026-09-06）

> 生成：OpenClaw（只读取证轮）。三份取证报告之二余：`MA_JIANTAO_GOLDEN_PIPELINE.md`、`OPENCLAW_VS_ZCODE_FACE_PIPELINE_DIFF.md`。
> 本轮 OpenClaw 对 `D:\FL26_Mod` 的写入**仅限本 reports 目录三个 .md**，其余零改动。

## 1. 当初成功的方法（一句话）

**照片（test01_front.jpg）→ Track D bake8 纹理烘焙（baked_ea3.png，修正坐标系 bug + MediaPipe 14 锚点）→ 铺满 6 张 eastAsia 图集（new5/6 直铺 + new2/3/4 重采样）→ avatar_ea3_v5.unity3d → fl26_allchina_v5.apk → 真机"中国队全员马健涛"。**
MICA 只做过几何实验（被放弃），纹理成功路线完全不依赖 MICA。

## 2. D 盘项目保留了多少成功资产 → **100%**

| 资产 | 状态 |
|---|---|
| golden 输入 test01_front.jpg / photo_111.png | ✅ 在（9/2 原时间戳） |
| track_d 全部 bake 产物（baked_ea3、ea3_remap_v5_*、bake_mask.npy 等） | ✅ 在（9/2–9/3 原时间戳） |
| bake8 / generate_candidates 原始脚本 | ✅ 未被修改（mjt 变体均为新文件） |
| avatar_ea3_v5.unity3d + fl26_allchina_v5.apk（冻结 SHA256） | ✅ 在 |
| 原始 avatar.unity3d / gamedata.unity3d / base.apk | ✅ SHA256 与 8/31 基线一致 |
| 历史 runs / candidates / 全部旧 APK | ✅ 未清理 |
| 历史报告 recon\reports\ | ✅ 全在 |

**结论：Zcode 复现失败不是资产丢失，而是输入与脚本链分叉（详见 DIFF 报告 §2）。**

## 3. Zcode 从哪一步开始偏离

2026-09-06 01:39，新增输入 `face_benchmark\inputs\mjt_new\mjt1.jpg`（非 golden 照片），随后重写 adapter/bake/render 脚本变体（`*_mjt.py`）。此前的 STEP10/11（Dashboard、final_face、E2E APK）属有效增量，不算偏离；但 `final_face\face_manifest.json` 在 9/6 10:42 被改写且与 STEP10 报告参数矛盾（b1/b7/b14 三处），需澄清。

## 4. 绝对不能覆盖的文件（PROTECTED 清单）

见 `MA_JIANTAO_GOLDEN_PIPELINE.md` §不可覆盖清单。特别强调：
- `dist\fl26_allchina_v5.apk`（真机最后的成功基线，STEP11 也以它为注入基座）
- `build\avatar_ea3_v5.unity3d`、`work\face_pipeline\track_d\baked_ea3.png`
- `face_benchmark\inputs\test01_front.jpg`
- `face_benchmark\runs\test01\final_face\baked.png`（c4，E2E 线当前纹理）
- 原始 `avatar.unity3d` / `gamedata.unity3d` / `working\base.apk`

## 5. 下一步最小修复点（建议，未执行、未授权）

1. **重放验证（半天内可完成）**：用 golden 输入 `test01_front.jpg` 原样运行未改动的 `face_benchmark\scripts\track_d_bake8.py`，比对输出与 `baked_ea3.png`（像素 diff / hash）。能复现 → 证明脚本链健康，问题只在输入/参数；不能复现 → 环境依赖（Python 包版本）问题，再查 `face_benchmark\envs\envs\recon`。
2. **新照片（mjt1-3.jpg）必须走同一 golden 链**：新图先过 `generate_candidates.py` 建立可比候选，再进 bake8，禁止绕过候选评估直接烘焙。
3. **澄清 face_manifest.json 矛盾**（b1/b7/b14 与 STEP10 报告不一致 + note 乱码），以人工调参的真实记录为准重建 manifest。
4. **完成 fl26_e2e.apk 真机验收**（STEP11 已 BLOCKED 于设备掉线）：这是 E2E 线转正为"第二基线"的唯一缺口。
5. MICA 复活线（adapter_*_mjt / render_mica_mjt1）在重放验证通过前**不建议投入**——9/3 已有"几何变形观感失败"的裁决。

## 6. 执行权归属（待 Daniel 裁决）

Golden Recipe 已完成取证。按任务约束，此刻才允许决定：
- **方案 O（OpenClaw 执行）**：第 1 步重放验证由 OpenClaw 跑（熟悉 bake8 的每个坑：x 取反、wrap 环回、逆映射 AFFINE）。
- **方案 Z（Zcode 执行）**：把本报告 + DIFF 报告交给 Zcode，要求先跑重放验证并回贴 diff 证据，再继续 mjt 新照片线。
- 无论谁执行：PROTECTED 清单全程生效，所有新产物写新文件名，不覆盖任何 9/2–9/3 资产。
