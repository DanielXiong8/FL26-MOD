# STEP10_MANUAL_TUNING_REPORT.md — FL26 Face Manual Tuning Dashboard

> 完成日期：2026-09-05。Step 10 = 把已经生成出来的脸变成**一个人可以操作、选择、微调和确认的工具**。
> 增量开发：未重做 MICA / Candidate Pool / UV 分析 / v5c / Player schema；未修改 OpenClaw workspace；
> 未删除历史 runs；未触碰原始 APK / AssetBundle。

## 1. Dashboard 位置与启动

- 位置：`D:\FL26_Mod\tools\FL26_FaceDashboard\dashboard.py`
- 启动：`python D:\FL26_Mod\tools\FL26_FaceDashboard\dashboard.py`（tkinter GUI，stdlib + Pillow）
- 自检：`python D:\FL26_Mod\tools\FL26_FaceDashboard\dashboard.py --selftest`（全部 PASS，写 `selftest_result.json`）
- 3D 渲染后端：`D:\FL26_Mod\tools\FL26_AvatarPreviewer\Assets\Scripts\Editor\DashboardRender.cs`（additive，Unity batchmode 渲染任务）

## 2. 功能与实测

| 功能 | 状态 | 说明 |
|---|---|---|
| A 输入照片 | ✅ | 支持多选（文件对话框，默认目录 `face_benchmark\inputs\`），原图路径记录进 manifest |
| B 生成 Candidate Pool | ✅ | 按钮直接调 `generate_candidates.py --input <photo> --n 8 --seed 20260903 --output <新 run 目录>`（异步线程，不复制逻辑） |
| C 候选看板 | ✅ | 卡片 = 缩略图(front.png) + score/tilt/seam/coverage + PASS/REJECT；REJECT 自动灰置禁选（metrics.csv 驱动） |
| D 人工调节 | ✅ | b1（42 值/7 家族下拉，**实时换纹理**）、b4（寸头/长发/中等）、b7（络腮/下巴撮/无）、b10（黑/棕/翻转标志）、b14（椭圆/稍尖/高额头）——全部离散下拉、带中文标签 |
| E 眼睛 | ✅ 占位 | 显示 `NOT YET EXPOSED（未确认字段，不开放）`，接口已保留 |
| F 实时 3D 预览 | ✅ | Orbit 相机 4 视角（front/45L/45R/side）+ **b1 换纹理实时可见**；b4/b7/b10/b14 记录到 manifest（真机生效），界面明确标注；rotate/zoom = Unity Play 模式交互预览（N/P/C 快捷键沿用） |
| G tuned candidate | ✅ | `c4_tuned_001/`（baked/front 副本 + `manual_tuning.json`：parameters_before/after/changes）；**原候选 SHA256 不变** |
| H ACCEPT FACE | ✅ | `final_face/`：baked.png + front.png + `face_manifest.json` + preview_* |

## 3. face_manifest.json（APK pipeline 接口，schema `fl26_final_face_v1`）

```json
{
  "source_photos": ["...test01_front.jpg"],
  "selected_candidate": "c4",
  "tuned_candidate": "c4_tuned_001",
  "appearance_patch": {"b1": 25, "b4": 0, "b7": 127, "b10": 0, "b14": 42},
  "appearance_note": "b0/b2/b3/... 其余字节保持 PlayerAppearanceTable 原记录值；APK 注入阶段只 patch 上述 5 字节",
  "b1_texture": "face_eastAsia_new4",
  "baked_texture": "final_face/baked.png",
  "preview_images": ["...preview_dash_front.png", ...],
  "validation": {"fault_metrics": {...}, "user_accepted": true},
  "provenance": {"pipeline": "MICA + face bake v1 + Candidate Pool v1 (frozen)", "generator_seed": 20260903}
}
```
姓名/位置/17 能力/球队**不在本阶段**——APK 注入阶段只读这个 manifest。

## 4. Gate 实测

| Gate | 状态 | 证据 |
|---|---|---|
| STEP10_INPUT_READY | 🟢 | 三张马健涛照片载入显示（selftest + GUI） |
| STEP10_CANDIDATE_VIEW_READY | 🟢 | test01 八候选卡片、c1/c2 REJECT 灰置（metrics.csv 实读） |
| STEP10_MANUAL_TUNING_READY | 🟢 | `c4_tuned_001/manual_tuning.json`：changes b1 22→25、b7 127→1 |
| STEP10_REALTIME_PREVIEW_READY | 🟢 | DashboardRender 实测：face_EastAsia_new2 + face_eastAsia_new5 纹理交换 → 4 张 orbit 渲染，马健涛脸可见（`renders/dashboard_test/`） |
| STEP10_FINAL_FACE_EXPORT_READY | 🟢 | `final_face_selftest/face_manifest.json` schema 校验通过 |
| STEP10_NONDESTRUCTIVE_READY | 🟢 | c4 原文件 SHA256 前后一致 |

## 5. 回归验证（Step 9 不受影响）

- Step9BatchRunner 重跑：**result=OK, errorCount=0, 16/16 captures**（含 c4 四视角 290-323KB）
- DashboardRender.cs 为纯新增文件；Step9BatchRunner.cs / PreviewerBootstrap.cs 零改动
- `PC_PREVIEW_VALID = GREEN` 保持

## 6. 已知限制（诚实记录）

1. **b4/b7/b10/b14 无 PC 预览效果**：这些字节控制真机运行时的头发/胡须网格与颜色选择（游戏按 appearance 挂接），PC 端渲染头部本体——参数会被记录并在真机生效，界面已明确标注（不伪造预览）。
2. **b14→具体网格映射未建立**：42/43/44 效果真机确认，但与 face_EastAsia_newX 网格的对应关系未逆向；记录后由 APK 阶段 patch。
3. **渲染约 1-2 分钟/次**：Unity batchmode 启动+导入开销；勾选"自动渲染"可边调边看，但高频改动建议手动触发。
4. **rotate/zoom 交互**：Dashboard 出图是固定 orbit 角度；连续旋转缩放请用 Unity Play 模式（工程已就绪，Play 后 N/P/C 快捷键）。
5. **Library 缓存偶发损坏**（MemoryStream corrupted）：连续强杀 Unity 进程的副作用；删 `Library/ArtifactDB`、`SourceAssetDB` 即恢复（本阶段已遇到并修复多次）。
