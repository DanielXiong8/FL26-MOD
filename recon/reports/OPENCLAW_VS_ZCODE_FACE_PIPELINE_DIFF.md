# OPENCLAW_VS_ZCODE_FACE_PIPELINE_DIFF.md — Golden vs 当前管线逐项 diff

> 生成：2026-09-06 11:30（OpenClaw，只读取证）。基线 = `MA_JIANTAO_GOLDEN_PIPELINE.md`（SUCCESSFUL_RUN_ID = ALLCHINA_V5C）。
> Zcode 侧证据 = `D:\FL26_Mod` 文件系统实测（LastWriteTime）+ Zcode 报告（STEP10/STEP11）+ 9/6 新增脚本。

## 0. Zcode 当前实际在做什么（实测）

9/5–9/6 Zcode 产线分两条：

- **E2E 线（STEP10/11，报告齐全）**：Dashboard 调参 → `final_face`（baked.png = c4）→ `phase11_e2e_inject.py` → `dist\fl26_e2e.apk`（构建 OK，真机因设备掉线 BLOCKED）。
- **Golden 复现线（9/6 01:39–01:52 + 09:56–11:16，无报告）**：新增 `inputs\mjt_new\mjt1-3.jpg` + `scripts\step11\adapter_stage{1,2,2b,2c}_mjt.py` + `track_d_bake8_mjt.py` → `track_d\baked_mjt_v1.png`（200KB，9/6 01:48）+ `render_mica_mjt1.py` / `render_final_mjt.py`；`final_face\face_manifest.json` 于 9/6 10:42 被改写。

## 1. 逐项 diff

| # | 步骤 | OPENCLAW_GOLDEN | ZCODE_CURRENT | 标记 |
|---|---|---|---|---|
| 1 | 输入照片 | `test01_front.jpg`（=photo_111.png，174KB，9/2） | 复现线改用 **`mjt_new\mjt1.jpg`（234KB，9/6 新图）**；E2E 线 manifest 仍记 test01-03 | **DIFFERENT（复现线）** |
| 2 | preprocess/warp | `warped_111.png`→`custom_face_111.png`（9/2 链） | 复现线重跑 bake8 变体（`bake8_stage1.png`/`bake8_stage2_shaded.png` 9/6 01:48） | **DIFFERENT** |
| 3 | landmark | MediaPipe face_landmarker_v2_with_blendshapes.task + 14 锚点 Procrustes | 同一 .task 文件仍在项目内；mjt 脚本是否同一用法未逐行审计 | **UNKNOWN** |
| 4 | MICA | MICA 不进 golden 纹理路线；几何注入实验被用户放弃 | 复现线重跑 `adapter_stage{1,2,2b,2c}_mjt.py`（MICA 适配链复活）+ render_mica_mjt1.py | **DIFFERENT / REGRESSION 风险** |
| 5 | bake 核心 | `track_d_bake8.py`（未改动，9/3 修复版）：(x,z) 平面+原生 UV 栅格化 → baked_ea3.png | **新写 `track_d_bake8_mjt.py`**（未改原脚本，好），产物 baked_mjt_v1.png | **DIFFERENT**（脚本分叉） |
| 6 | UV / 图集映射 | ea3 → 6 张 eastAsia 图集（new5/6 同构直铺；new2/3/4 重采样 `ea3_remap_v5_*.png`） | 复现线尚未见 ea3_remap_mjt 对应产物（截至 9/6 01:48） | **UNKNOWN** |
| 7 | color/lighting | weak/conservative（c4 参数：light=0.5, align=conservative） | E2E 线沿用 c4；复现线参数未记录 | **SAME(E2E)/UNKNOWN(复现)** |
| 8 | final_face | golden 无此概念（直接 ea3 铺图集） | c4 baked.png + `face_manifest.json`（**9/6 10:42 被改写**：b1=22, b4=127, b7=127, b10=0, b14=33；与 STEP10 报告 b1=25/b7=1/b14=42 矛盾） | **DIFFERENT + 冲突** |
| 9 | appearance bytes | allchina 轮不改 PA（全员原生 b1 22-27 命中替换贴图） | E2E 注入 pid 175923 "Ma Jiantao" + PA 克隆 Ralla patch b1=22/b4=0/b7=127/b10=0/b14=42→33 | **DIFFERENT**（两条不同机制） |
| 10 | avatar bundle | `avatar_ea3_v5.unity3d`（dc7af4e9…9630，冻结） | E2E 以 fl26_allchina_v5.apk 为基座再注入 gamedata/avatar（`phase11_e2e_avatar_inject.py` 9/6 01:52） | **SAME（基座被正确复用）** |
| 11 | APK | fl26_allchina_v5.apk（真机 Success） | `dist\fl26_e2e.apk`（sign OK，**真机未验证**，设备掉线 BLOCKED） | **DIFFERENT + 未验证** |
| 12 | 真机证据 | v4/v5c 用户目视："很多像马健涛的球员" | 无（STEP11 三 Gate BLOCKED） | **REGRESSION** |

## 2. 第一个导致偏离的步骤

**Step 1（输入照片）**。9/6 01:39 Zcode 引入 `mjt_new\mjt1.jpg` 作为复现输入，而不是 golden 输入 `test01_front.jpg`。此后每一步（warp、bake、render）都是在**新输入 + 新脚本变体**上重新推导，与 golden 资产（baked_ea3.png 及其参数）失去逐级可比性。换言之：**Zcode 不是"复现失败"，而是从一开始就在跑另一条实验线**，同时 golden 资产完好无损。

次要风险点：MICA 适配链复活（Step 4）——golden 裁决中 MICA 几何路线已被用户明确放弃（脸拉长/光头），若复现线以 MICA 形变为主视觉，即使纹理复现成功也会重蹈 9/3 的失败观感。[C，需 Zcode 确认其 render_mica_mjt1.py 的意图]

## 3. 冲突与矛盾记录（保留原状，未修改）

1. `final_face\face_manifest.json`（9/6 10:42 版）：b1=22 / b4=127 / b14=33，b1_texture="face_eastAsia_new1 (Kue N. head-model clone…b14=33)"——与 STEP10 报告（b1 22→25、b7 127→1、b14=42）**直接矛盾**。manifest 内中文 note 有 UTF-8 乱码（GBK/UTF8 混写痕迹）。
2. `phase11_e2e_inject.py` 最后写入 9/6 11:16（本轮取证前 3 分钟），说明 Zcode 仍在活跃迭代该文件。
3. `dist\` 目录 9/6 11:17 有更新（未逐文件核对新增 APK）。

## 4. 结论

- Zcode 对 golden 资产**零破坏**：track_d 9/2–9/3 产物、avatar_ea3_v5、全部历史 APK 均在，脚本原版未改（mjt 变体全是新文件）。✅
- 偏离起点 = 输入照片更换（9/6 01:39），叠加"重写脚本"而非"重放脚本"。
- E2E 线（STEP10/11）是有效增量（Dashboard/manifest/APK 注入接口），与 golden 不冲突，但**其真机验证尚未完成**，不能当作新的成功基线。
