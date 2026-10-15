# OPENCLAW_GOLDEN_FACE_PIPELINE.md — 马健涛 Golden Face Recipe（可复现版）

> 生成：2026-09-06（Phase 13A）。性质：从 OpenClaw 记忆 + D:\FL26_Mod 实际产物中提取的**可重复执行 Recipe**。
> GOLDEN_RUN_ID = **ALLCHINA_V5C**（2026-09-03，真机 95e2d9a 验证，用户裁决"已有足够多像马健涛的球员"）。
> 本文件 = 唯一权威 Golden Reference。所有路径已通过 junction `C:\FL26_Mod → D:\FL26_Mod` 双向可用。

---

## 1. Golden Run

```
GOLDEN_RUN_ID = ALLCHINA_V5C
日期：2026-09-03 09:09（bake8 完成）～ 15:30（APK 安装）
设备：小米 24129PN74C（95e2d9a），MIUI HyperOS
用户裁决：v4 6/6 马健涛贴图 → v5c 中线裂缝未修但"已有足够多像马健涛的球员（Ling L/Wan S/Yang J）"→ 归档为成功基线
```

## 2. Input

| 文件 | SHA256（前16） | 大小 | 说明 |
|---|---|---|---|
| `face_benchmark\inputs\test01_front.jpg` | d5c409211311e6a7 | 174,354 B | **主照片**（= photo_111.png 同一文件） |
| `work\face_pipeline\track_d\photo_111.png` | d5c409211311e6a7 | 174,354 B | 工作副本（bake8 直接读取） |
| `work\face_pipeline\track_d\baseline_eastasia_new1.png` | f94a31990a260f21 | 135,822 B | eastAsia_new1 原生贴图（光照迁移基准） |
| `work\face_pipeline\uv\mesh_ea1.json` | df87a530d4b8b061 | 115,787 B | ea1 模板网格（700顶点/UV/三角形） |
| `work\face_pipeline\uv\uv_landmark_map.json` | 2165f7dc18968672 | 5,929 B | 19 语义锚点（3D→UV 映射） |
| `work\face_pipeline\face_landmarker_v2_with_blendshapes.task` | — | 3,758,596 B | MediaPipe FaceLandmarker 模型 |

**test02/test03**：后续扩展输入，golden bake 链只消费 test01/photo_111。

## 3. Preprocess

bake8 内联完成（无独立预处理脚本）：
- cv2 读图 → RGB
- MediaPipe FaceLandmarker（478 landmarks，`face_landmarker_v2_with_blendshapes.task`）
- 语义锚点：MP idx 对（如 left_eye=[33,133]）→ 13 锚点均值坐标

## 4. MICA（几何重建，v5c 中仅用于 new1 网格）

| 项 | 值 |
|---|---|
| 运行器 | `face_benchmark\repos\MICA\demo.py`（`-i <img_dir> -o outputs/mica -m data/pretrained/mica.tar`） |
| Checkpoint | `data/pretrained/mica.tar`（arcface + flameModel） |
| 输入 | test01_front.jpg（outputs/mica/test01_front/ = 重建结果） |
| 输出 | mesh.obj（FLAME 5023顶点/mm/Y-up）+ identity.npy(332维) + kpt68/kpt7.npy |
| 渲染基准 | final_front.png（正面灰模，用户确认"像马健涛"的面部骨架） |

**v5c 对 MICA 的使用**：仅 new1 网格注入 MICA 适配顶点（经 adapter stage2c）。new2-6 用原生网格。MICA 全面网格注入（5/6 张）已被用户放弃（"脸拉长+光头"）。

## 5. FL26 Adapter（MICA → ea1 模板适配）

四阶段脚本（`face_benchmark\scripts\`，**原版未改动**）：

| 阶段 | 脚本 | 输入 | 输出 | 关键参数 |
|---|---|---|---|---|
| Stage1 | adapter_stage1.py | MICA mesh.obj + mesh_se3.json + uv_landmark_map.json | stage1_alignment.json | 19 语义锚点、相似变换（刚性10锚点）、残差 10.5mm |
| Stage2 | adapter_stage2.py | stage1 + MICA mesh | stage2_adapted.json + fl26_adapted.obj | FLAME ibug68 → FL26 锚点逐顶点映射 |
| Stage2b | adapter_stage2b_tps.py | stage2 | stage2_tps.json + fl26_adapted_tps.obj | TPS + alpha 混合（alpha=0.447±0.465） |
| Stage2c | adapter_stage2c_ea1.py | stage2b + mesh_ea1.json | **stage2_ea1.json + fl26_ea1_adapted.obj** | ea1 距离 falloff 混合 |

**注意**：当前 `fl26_ea1_adapted.obj` 已被 Phase 12 的 mjt1 重跑覆盖。原始 test01 版可从 v5c bundle 的 face_EastAsia_new1 网格顶点恢复（x 翻转约定）。

## 6. Template

| 项 | 值 |
|---|---|
| 目标网格 | face_EastAsia_new1（700顶点/1254三角形/submesh0=眼球32面/submesh1=脸1222面） |
| stream0 stride | 40（pos3+normal3+tangent4+uv2 = 12 floats）；uv0 = stream1 offset0 |
| 坐标约定 | 游戏资产 X = mesh_ea1.json X × (-1)（**写回需 x 取反**） |
| 顶点写入 | 逐顶点 12B float32（pos only，normals/tangents 不动） |
| 家族拓扑 | new5/6 与 new1 UV 同构（顶点序不同）；new2/3/4 独立图集；new4=698顶点拓扑不同 |

## 7. Bake（bake8 = track_d_bake8.py，**核心**）

### 参数链

| 步骤 | 参数 |
|---|---|
| 渲染平面 | RS=1024，(x,z) 平面（**Z-up 修正**，bake7 的 bug），crop FX=(-0.10,0.10), FZ=(-0.16,0.16) |
| 语义锚点 | MediaPipe 14 锚点（MP_PAIRS：left_eye=[33,133] 等），mesh 最近顶点 3D→渲染平面 |
| 左右手检测 | flipLR True/False 双试，取 Procrustes 残差最小者 |
| Procrustes | 相似变换（旋转+均匀缩放+平移），SVD 分解 |
| 鲁棒重拟合 | 丢弃残差 > max(2×median, 15px) 的锚点，≥6 inliers 重拟合 |
| 光照迁移 | baseline 原生 UV 正面栅格化 vs warped photo → Gaussian(σ=20) 灰度比值 → 乘回 |
| 烘焙栅格化 | 原生 UV 三角形（bake_t = FN_z > 0.55），barycentric 插值，z-buffer by FN_z |
| alpha 羽化 | mask > 0 → Gaussian(σ=1.5) → base×(1-α) + baked×α |
| 输出 | baked_ea3.png（512×512，烘焙区域 26,223px = 10.0%） |

### 输出

- `work\face_pipeline\track_d\baked_ea3.png`（190,805 B）— **golden 烘焙**
- 复现验证（2026-09-06）：junction 重放 → 视觉一致（像素差 mean=0.02, max=8）

## 8. Appearance

### allchina v5c 的外观状态

- **PlayerAppearanceTable：golden 轮未修改**（纯贴图替换路线）
- 中国队球员：原生 PA 记录（b1 分布 10-15 = face_America 家族 + 部分其他）
- **Ralla (103346)**：b1 30→22、b7 0→127（build 脚本中唯一 PA patch，测试验证用）

### 贴图替换机制（为什么"中国队全员马健涛"）

中国队球员 b1 = 10-15 → face_America_new1-6 家族 → **但 allchina 替换的是 face_eastAsia_new1-6** ——

**修正理解**：v5c 替换后，中国队球员脸变马健涛的机制 = **b14（FACE_SHAPE_MESH）决定头网格变体**，网格变体的 UV 布局与 face_eastAsia 图集对应；b1 决定贴图族。allchina 贴图替换后，**所有引用 eastAsia 图集的头网格**（无论 b1 实际值）都渲染马健涛贴图。其余细节（fa/fb/fc 头模代码）控制具体头模变体选择。

### E2E 球员注入（Face Builder v1 验证）

| 字节/字段 | 值 | 来源 |
|---|---|---|
| Players.fa/fb/fc | 0,0,0 | arsenal_v3 风格（无头模引用） |
| Players.nat | 13→按需 | 国家队征召需匹配目标队国籍代码 |
| Players.b1 | 3 (FW) | 位置代码 |
| PA record | 克隆目标队友完整 17B | 保证渲染一致 |

## 9. APK Injection

| 步骤 | 命令/脚本 |
|---|---|
| gamedata 注入 | `scripts\build_ea3_allchina_v5.py`（Players append + ClubPlayer insert + PA patch + avatar bundle 打包） |
| avatar 打包 | face_EastAsia_new1 网格(MICA verts) + face_eastAsia_new1/5/6 贴图(ea3) + face_eastAsia_new2/3/4 贴图(重映射) |
| APK 重打包 | 替换 assets/bundles/gamedata.unity3d + avatar.unity3d → zipalign -p -f 4 → apksigner sign（fl26_test.keystore） |
| 安装 | adb install -r（设备 95e2d9a） |

## 10. Android Evidence

- **中国队全员马健涛**：用户真机目视确认（v4/v5/v5c 多轮）✓
- **球员卡属性显示**：CustomeagueTest 六维 79-97 区间（inject 后 UI 计算）✓
- **比赛进行**：SUN 0-3 LCR 45:50（完整半场以上）✓
- **截图存档**：`screenshots\fl26_v3/v5/v6_squad/scroll/roster*.png`（9/1 00:56-01:17）

## 11. Reproduction Command

```bash
# 前置：junction C:\FL26_Mod → D:\FL26_Mod（已创建）
cd D:\FL26_Mod\face_benchmark\repos\MICA
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe demo.py -i D:\FL26_Mod\face_benchmark\inputs -o D:\FL26_Mod\face_benchmark\outputs\mica -m data/pretrained/mica.tar

cd D:\FL26_Mod\face_benchmark\scripts
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe adapter_stage1.py
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe adapter_stage2.py
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe adapter_stage2b_tps.py
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe adapter_stage2c_ea1.py

D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe track_d_bake8.py

cd D:\FL26_Mod\scripts
D:\FL26_Mod\face_benchmark\envs\envs\recon\python.exe build_ea3_allchina_v5.py

D:\FL26_Mod\android-sdk\platform-tools\adb.exe install -r D:\FL26_Mod\dist\fl26_allchina_v5.apk
```

**重放验证（2026-09-06）**：bake8 原样重放 → baked_ea3.png 视觉一致（像素差 mean=0.02, max=8, 2.4% 非零）✓

## 12. Known Failure Modes

| 失败模式 | 原因 | 修复/状态 |
|---|---|---|
| bake7 眼区倾斜 5.5° | Z-up 网格被当 x,y 渲染平面（俯视渲染） | bake8 改 (x,z) 平面 ✓ |
| bake4_magenta 全员黑脸 | PIL transform(AFFINE) 误用正向系数（需逆映射 dst→src） | v5 修正 ✓ |
| v5 首装黑脸 | 同上（正向/逆向映射错误） | v5 修正 ✓ |
| v5b 竖黑条 | PIL 越界填黑（wrap 环回缺失） | v5b wrap 双线性修 ✓ |
| v5c 中线裂缝 | 图集中线两侧采样方向差 | **未修，用户裁决归档** |
| MICA 全网格注入 "脸拉长+光头" | MICA 变形量过大（仅 new1 保留 MICA verts） | 放弃全面注入 |
| 新 PID 180001 ROSTER_GATE 过滤 | 超过内部 ID 检查/缺外观索引 | 改顺序 ID 175923 ✓ |
| fa/fb/fc 非零且引用不存在头模 | 玩家模型加载失败 → 阵容隐藏 | fa/fb/fc=0 或克隆真实队友 ✓ |
| 10027 ≠ 真实中国队 | 10027 = 游戏生成占位队；真实中国队 = 10059 | 已修正 ✓ |
| 国家队阵容 ≠ ClubPlayer 直读 | 国家队有独立征召/过滤层 | 待逆向（不阻塞 League） |

## 13. Golden Artifacts（SHA256 清单）

| 文件 | SHA256（前16） | 大小 |
|---|---|---|
| test01_front.jpg | d5c409211311e6a7 | 174,354 |
| photo_111.png | d5c409211311e6a7 | 174,354 |
| baseline_eastasia_new1.png | f94a31990a260f21 | 135,822 |
| mesh_ea1.json | df87a530d4b8b061 | 115,787 |
| uv_landmark_map.json | 2165f7dc18968672 | 5,929 |
| MICA mesh.obj | 5931bfb6e6b1fb6a | 359,468 |
| MICA final_front.png | acbf612766917155 | 47,267 |
| baked_ea3.png（原版） | **bd172b9cdcb20f1c** | 190,643 |
| ea3_remap_v5_new2/3/4.png | b0e42401/c149406d/66d467f1 | 88-94KB |
| avatar_ea3_v5.unity3d | dc7af4e9dab303df | 71,573,122 |
| fl26_allchina_v5.apk | 77c825ecfe564625 | 442,289,329 |
| track_d_bake8.py | b389a3cd49644acd | 10,008 |
| build_ea3_allchina_v5.py | b9d4d73805729871 | 9,874 |

**GOLDEN_FACE_PIPELINE_LOCKED** = 上述 SHA256 + 本文件 = 完整 Golden 基线。
