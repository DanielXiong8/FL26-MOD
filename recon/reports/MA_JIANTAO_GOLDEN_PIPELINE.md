# MA_JIANTAO_GOLDEN_PIPELINE.md — 马健涛换脸 Golden Recipe（OpenClaw 取证版）

> 生成：2026-09-06 11:30（OpenClaw）。性质：**只读取证**，未修改任何 pipeline / Zcode 产物 / 原始资产。
> 证据来源：OpenClaw memory（`memory/2026-09-02.md`、`2026-09-03.md`）+ `D:\FL26_Mod` 文件系统实测（LastWriteTime / 文件存在性）。
> 置信度标注：**[A]** = 文件/日志直接可见；**[B]** = 多源记忆一致；**[C]** = 推断，需验证。

---

## 0. SUCCESSFUL_RUN_ID

```
SUCCESSFUL_RUN_ID = ALLCHINA_V5C
（track_d bake8 → baked_ea3.png → ea3_remap_v5_new2/3/4 → avatar_ea3_v5.unity3d
  → fl26_allchina_v5.apk，2026-09-03 15:30–16:00，C:\FL26_Mod 时期，真机 95e2d9a 安装 Success [A]）
```

**用户裁决记录 [A]**（memory/2026-09-03.md L68-102）：
- v4 真机：6/6 球员呈现马健涛贴图（new2/3/4 用 3D-NN + griddata 重采样）。
- v5c 真机（15:54）：中线裂缝未修好，**用户裁决"不再追修——已有足够多像马健涛的球员（Ling L / Wan S / Yang J）"**。
- 真正让用户满意的是**纹理替换路线（allchina）**，不是 MICA 几何变形路线（avatar_ea3_mica：部分亚洲脸拉长+光头，被放弃）。

冻结基线 SHA256 [A]（ZCODE_HANDOVER.md §7）：
- `build\avatar_ea3_v5.unity3d` = `dc7af4e9…9630`
- `dist\fl26_allchina_v5.apk` = `77c825ec…8391`

---

## A. 输入

| 项 | 内容 | 置信度 |
|---|---|---|
| Primary input | `face_benchmark\inputs\test01_front.jpg`（174,354 B，9/2 17:12）＝ Candidate Pool 的 `photo_111.png` 同一文件（config.json input 字段直证） | [A] |
| 辅助照片 | `test02_front.jpg`（134,248 B）、`test03_front.jpg`（114,222 B，9/2 20:29/20:38）——test02/03 为后续扩展输入，golden bake 链只消费 test01/photo_111 | [A] |
| track_d 工作副本 | `work\face_pipeline\track_d\photo_111.png`（174,354 B，9/2 17:12）→ `warped_111.png` → `custom_face_111.png`（213 KB） | [A] |
| 尺寸 | 未在记忆/报告中显式记录 → **UNKNOWN**（可从 PNG header 读出，未改动任何文件即可获取） | — |

⚠️ 注意：Zcode 9/6 01:39 新增的 `inputs\mjt_new\mjt1-3.jpg` **不属于 Golden 输入**，是复现尝试的新输入（见 DIFF 报告）。

## B. 人脸检测 / landmark

- MediaPipe Face Landmarker：`work\face_pipeline\face_landmarker_v2_with_blendshapes.task`（3,758,596 B）[A]
- bake8 采用 **MediaPipe 14 语义锚点 + Procrustes 对齐** [B]（memory 09-03 + OPENCLAW_FL26_HANDOVER A5）
- 早期 bake 链有 loose+flip 兜底（错误投影下硬拉检测），bake8 已废弃该做法 [A]
- 裁剪/对齐/padding 参数具体数值：**UNKNOWN**（在 bake 脚本内，未逐行审计）

## C. MICA

Golden 纹理路线中 **MICA 不参与烘焙**（"纹理烘焙不依赖 MICA 几何：照片→FL26 UV 直接贴" [A]，memory 09-02 L30）。
MICA 仅用于几何适配实验线（与 SUCCESSFUL_RUN 并行、未被用户采纳进正式脸）：

- Checkpoint：MICA（FLAME 拓扑 5023 顶点 / mm / Y-up + identity 332 维 + 68 landmarks），输出目录 `face_benchmark\outputs\mica\test0{1-3}_front\` [A]
- Stage1：相似变换对齐，刚性核心 10 锚点，残差 10.5mm（中心区）[B]
- Stage2c：TPS，ea1 模板 14 锚点 → MICA 形状，nose 距离 falloff 混合；输出 `adapter\fl26_ea1_adapted.obj` + `stage2_ea1.json` [B]
- reg / landmark weight / identity weight 具体数值：**UNKNOWN**（Checkpoint 配置文件未在本轮取证中打开）
- MICA 顶点注入网格实验：5/6 张 eastAsia 网格（new4 跳过），UnityPy roundtrip 0 误差，真机生效但变形 → **放弃** [A]

## D. FL26 template fitting

- 拓扑事实 [A]：ea1(eastAsia_new1) ≡ se3(southeuropean_new3)：700 顶点 / 1254 三角形 / UV 全同，仅 blendshape 不同 → `uv_landmark_map.json` 锚点 v_idx 通用
- eastAsia 家族 [A]：new5/6 与 new1 UV 同构（顶点序不同）；new2/3/4 独立图集；**new4 = 698 顶点，拓扑不同**
- Golden 路线的"fitting"不是几何 fitting，而是**纹理域对应**：new2/3/4 用 **3D 最近邻顶点对应 + scipy griddata** 把 ea3 纹理重采样进各自图集（v4）→ v5 升级为**逐三角仿射光栅化 + 眼球收缩 15%** [A/B]
- Mesh 工程约束 [A]：stream0 stride=40，uv0=stream1 offset0；index uint16；submesh0=眼球(32面)/submesh1=脸(1222面)；**写回 x 取反**

## E. Texture baking（核心）

| 项 | Golden 值 |
|---|---|
| source texture | `track_d\photo_111.png`（= test01_front.jpg） |
| 关键中间产物 | `warped_111.png`(278KB) → `custom_face_111.png`(213KB) → `baked_111.png`(146KB, 9/2 17:32)；`bake_mask.npy` |
| 最终 bake | **`baked_ea3.png`（190KB，9/3 9:09，bake8 产物）** — bake7 发现坐标系 bug（Z-up 网格被当 x,y 渲染平面 → 等于俯视渲染，眼区倾斜 5.5°），bake8 修复：(x,z) 平面 + MediaPipe 14 锚点 Procrustes + 原生 UV 栅格化 → 眼区倾斜 0.8° [A] |
| FL26 texture target | face_eastAsia_new1（+ new5/6 同构直铺；new2/3/4 重采样） |
| texture resolution | 游戏脸纹理 512×512 RGBA（85 张）[A] |
| mask | `bake_mask.npy`（1,048,704 B = 512×512 float64）[A] |
| lighting/color | 前期有 `front_view_eq.png`（直方图均衡实验）；bake8 主链参数未逐项记录 → UNKNOWN |
| seam | v4：griddata 重采样；v5：逐三角仿射；v5b：**wrap 环回**修竖黑条（PIL 越界填黑教训）；v5c：wrap 双线性(scipy map_coordinates order=1 mode='wrap') + 接缝列递归羽化 → **中线裂缝仍未修好，用户裁决归档** [A] |
| eye/mouth | v5 眼球收缩 15%；b1（=ea1）mesh 眼/眉 landmark 3D 采样语义可疑但对称（对相似变换影响有限）[B] |
| new1/new2/new3/new4 用途 | new1=主 bake 目标；new5/6=UV 同构直铺；new2/3/4=3D-NN/griddata(v4)→逐三角仿射(v5) 重采样进各自图集，产物 `ea3_remap_new{2,3,4}.png` 与 `ea3_remap_v5_new{2,3,4}.png`（均完好保留于 track_d）[A] |

## F. 最终注入

| 项 | Golden 值 |
|---|---|
| baked texture | baked_ea3.png → 6 张 eastAsia 图集内容全替换（他们 b1 原生 22-27，故中国队全员变马健涛脸）[A] |
| avatar bundle | `build\avatar_ea3_v5.unity3d`（SHA256 dc7af4e9…9630）[A] |
| PlayerAppearanceTable | Golden allchina 轮**未改 PA 表**（纯贴图替换）；PA 修改路线（b1=22/b4/b7/b10/b14 patch）是后续 Zcode E2E 线，见 DIFF 报告 |
| 注入方式 | UnityPy 1.25.3 `read_typetree` → 改 dict → `save_typetree`；重打包 avatar.unity3d → zipalign → apksigner（build\fl26_test.keystore）→ adb install（设备 95e2d9a）[A] |
| APK | `dist\fl26_allchina_v5.apk`（v5c，最后真机安装版）[A] |

## G. Android 真机证据（GOLDEN BASELINE）

- 设备 95e2d9a，9/3 多轮 `adb install` Success [A]
- v4 真机：6/6 马健涛贴图呈现 [A]
- v5c 真机裁决（用户原话级记录）："已有很多像马健涛的球员：Ling L / Wan S / Yang J" [A]
- GOLDEN BASELINE APK = **`dist\fl26_allchina_v5.apk`**（= v5c，STEP11 记录"设备当前安装的马健涛 mod" [A]）
- 截图资产：`screenshots\` 目录（含 fl26_squad_scroll.png / fl26_v5.png 等 9/1 截图；9/3 allchina v4/v5 真机截图是否落盘 **UNKNOWN**，主要证据是用户目视反馈记录）

---

## 不可覆盖清单（PROTECTED）

1. `work\face_pipeline\track_d\` 全部 9/2–9/3 产物（baked_ea3.png、ea3_remap_v5_*.png、bake_mask.npy、photo_111.png、custom_face_111.png）
2. `build\avatar_ea3_v5.unity3d`、`dist\fl26_allchina_v5.apk`（含历史所有 fl26_allchina_* / avatar_ea3_* 变体）
3. `face_benchmark\inputs\test01_front.jpg`（golden primary input）
4. `face_benchmark\scripts\track_d_bake8.py`（bake 修复版基线）与 `generate_candidates.py`
5. `face_benchmark\runs\test01\`（candidates c1-c8、metrics.csv、config.json）
6. `build\avatar.unity3d` / `build\gamedata.unity3d`（原始资产，SHA256 已冻结于 ZCODE_HANDOVER §7）
7. `recon\reports\` 全部既有报告

## 下一步最小修复点（建议，未执行）

Golden 管线的一切资产都在且完好。Zcode 复现失败不是资产丢失，而是**换了输入照片 + 重写了脚本链**。最小修复 = 用 golden 输入 `test01_front.jpg` 走未改动的 `track_d_bake8.py` 重放，先对比 `baked_ea3.png` 是否可复现，再引入新照片。详见 DIFF 报告 §结论。
