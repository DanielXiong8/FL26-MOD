# OPENCLAW_VS_CURRENT_PIPELINE.md — Golden vs Face Builder v1 逐项对比

> 日期：2026-09-06。判定标准：SAME = 实质一致；DIFFERENT = 实质不同；MISSING = 缺失；UNKNOWN = 未确认；REGRESSION = 退步。
> 比较对象：**Golden = ALLCHINA_V5C**（test01_front → bake8 → ea3 bake → allchina v5c APK，真机验证 ✓）
> vs **当前 = Face Builder v1**（任意照片 → Candidate Pool → Dashboard 选脸 → c4/tuned bake → 注入 → APK）

---

## 1. 输入层

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| 照片来源 | test01_front.jpg（= photo_111.png） | 用户自选任意正面照 | SAME（机制相同） |
| 尺寸/裁剪 | 174,354 B，未记录裁剪参数 | 由 generate_candidates.py 处理 | UNKNOWN |
| 人脸 bounding box | bake8 内联 MediaPipe 检测 | generate_candidates.py 内联检测 | SAME（同为 MediaPipe） |
| 对齐 | Procrustes 相似变换（14 锚点，鲁棒重拟合） | generate_candidates.py 的 align 参数（conservative/normal） | DIFFERENT（参数空间不同） |
| landmark | MediaPipe 478 → 14 语义锚点 | 同（generate_candidates 内部） | SAME |

**判定：输入层 SAME**（同工具族、同 MediaPipe；参数差异属 Candidate Pool 设计特性）

## 2. MICA

| 项 | Golden (ALLCHINA_V5C) | 当前 Face Builder v1 | 判定 |
|---|---|---|---|
| MICA 参与度 | **仅 new1 网格注入 MICA verts**（new2-6 原生网格） | 完全不使用 MICA（Candidate Pool 不含 MICA） | **DIFFERENT** |
| checkpoint | mica.tar（data/pretrained/） | 不适用 | — |
| regularization/identity weight | demo.py 默认（未显式调参） | 不适用 | — |
| MICA 输出目录 | outputs/mica/test01_front/ | 不适用 | — |
| MICA 渲染基准 | final_front.png（面部骨架，用户确认"像"） | 不适用 | — |

**判定：DIFFERENT（实质性）**。Golden 路线 new1 网格含 MICA 形状；当前 v1 的 new1 网格 = 原生 eastAsia_new1（无 MICA 注入）。这是**面部骨架相似度**的关键差异来源——Golden 的 new1 网格 = 马健涛的面部骨架（眼距/鼻梁/下颌从照片重建），当前 v1 的 new1 网格 = 游戏原生模板形状。

## 3. FL26 Adapter

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| stage1 相似变换 | residual 10.5mm（10 刚性锚点） | 不适用（无 MICA→无适配） | MISSING |
| stage2 顶点映射 | FLAME ibug68 → FL26 锚点 | 不适用 | MISSING |
| stage2b TPS | alpha=0.447±0.465 | 不适用 | MISSING |
| stage2c ea1 falloff | nose 距离混合 | 不适用 | MISSING |
| 产物 | fl26_ea1_adapted.obj + stage2_ea1.json | 不适用 | MISSING |

**判定：当前 MISSING**（整个 adapter 链在当前 v1 流程中未使用——因为无 MICA 输入）。这是 Phase 13 的核心恢复目标。

## 4. Template

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| 目标网格 | face_EastAsia_new1（含 MICA verts） | face_EastAsia_new1（原生 verts，无 MICA） | **REGRESSION** |
| 头网格变体 | new1（b14=31 映射假设） | 按 b14=31 选择 | SAME（假设待验证） |
| mesh_ea1.json UV | ea1 模板 UV（bake 目标） | 同（bake 目标） | SAME |

## 5. Bake

| 项 | Golden (bake8) | 当前 (Candidate Pool) | 判定 |
|---|---|---|---|
| 脚本 | track_d_bake8.py（原版） | generate_candidates.py 内部 bake 变体 | **DIFFERENT** |
| 照片 | photo_111.png (test01) | 用户自选照片 | SAME（机制） |
| 对齐 | Procrustes 14锚点+鲁棒重拟合 | 参数化（reg/lmw/align/light 四维网格） | **DIFFERENT** |
| 参数 | 固定（bake8 内联值） | c4 = reg:mid, lmw:normal, align:conservative, light:weak | **DIFFERENT** |
| 光照迁移 | baseline 低频亮度比值 | light 参数控制（weak/normal/strong） | DIFFERENT |
| 输出分辨率 | 512×512（游戏贴图原生） | 512×512 | SAME |
| 覆盖率 | 10.0%（26,223px） | ~10%（按 metrics.csv） | SAME |

**判定：DIFFERENT（实质性）**。Golden = bake8 单一参数集；当前 = Candidate Pool 参数化变体。c4 的参数（light=weak）与 bake8 默认不同。

## 6. FL26 appearance

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| Ralla PA patch | b1=22, b7=127（测试验证） | 不适用（v1 流程无 Ralla patch） | N/A |
| E2E 球员 PA | 无（golden 无新球员注入） | 克隆队友 + b14=31 | **DIFFERENT**（新增能力） |
| Players fa/fb/fc | 0,0,0（arsenal_v3 风格） | 0,0,0（arsenal_v3 风格） | SAME |
| nat | 13（arsenal_v3） | 13 | SAME |
| b1 (位置) | 3 (FW) | 3 (FW) | SAME |

## 7. APK Injection

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| 替换 bundle | gamedata + avatar | gamedata + avatar | SAME |
| zipalign | -p -f 4 | -p -f 4 | SAME |
| apksigner | fl26_test.keystore v1+v2+v3 | 同 | SAME |
| 安装 | adb install -r | adb install -r | SAME |

## 8. Android Evidence

| 项 | Golden | 当前 | 判定 |
|---|---|---|---|
| 中国队全员马健涛 | ✓ 用户目视确认 | ✓ 同一 avatar bundle | SAME |
| League 球员出现 | N/A（golden 无新球员注入） | ✓ Man City 阵容出现（用户确认） | **DIFFERENT（新增能力）** |
| 完整比赛 | ✓ 多场比赛 | ✅ 待最终确认 | PENDING |
| 脸部特写 | 用户裁决"像马健涛" | 用户确认"在，像！" | SAME |

## 9. 综合判定

### 导致当前与 Golden 分叉的第一个步骤

**Bake 参数差异**。Golden 用 bake8 固定参数集（light 迁移含 baseline 比值）；当前用 Candidate Pool 的参数变体（c4 = light:weak）。这导致烘焙纹理的光照/色调不同 → 最终渲染的肤色/亮度差异。

### 导致面部骨架差异的步骤

**MICA 顶点注入**。Golden 的 new1 网格 = MICA 拟合的马健涛面部骨架；当前 v1 的 new1 网格 = 原生 eastAsia 模板。这是面部骨架相似度的核心差异。

### 回归项

1. **face_EastAsia_new1 网格**：当前 = 原生模板（缺 MICA verts）vs Golden = MICA 注入版 → **REGRESSION**
2. **face_eastAsia_new1 贴图**：当前 = ea3 烘焙（golden 同一文件）→ SAME
3. **b14 选择器**：31 → face_EastAsia_new1 映射假设**未最终验证** → UNKNOWN

## 10. 修复方向（Phase 13 优先级）

1. **恢复 MICA verts 注入**（从 outputs/mica/test01_front/ + adapter 链重新生成 → 注入 face_EastAsia_new1）— 恢复面部骨架
2. **bake 对齐**（用 golden bake 参数替代 Candidate Pool 的 light:weak 变体）— 恢复纹理光照
3. **b14 映射验证**（真机 A/B：b14=31 vs 32-36 对比脸形变化）
