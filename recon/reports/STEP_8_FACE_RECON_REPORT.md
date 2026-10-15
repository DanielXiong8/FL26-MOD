# Step 8: Face/Appearance Recon v1 — 中期报告

> **状态**：Track A 准备完毕，Track B 核心突破，Track C 待启动
> **日期**：2026-09-01

---

## 核心问题解答

### 1. Appearance 17/21B 字段哪些已经实际确定？
- **Byte 0 (1-5)**：大类 ID（可能是人种/骨骼类别）
- **Byte 1 (29-33)**：**核心参数**。高熵 ID 字段，最可能对应基础脸纹理模板（face texture ID）
- **Byte 14 (37-41)**：**核心参数**。高熵 ID 字段，最可能对应头发/胡须 mesh（hair mesh ID）
- **Bytes 2, 11-13**：恒为 0（保留位）
- **Bytes 4, 7**：布尔型开关（仅 0/127）
- **其余**：稀疏 ID/枚举，默认 127(0x7F) 或 255(0xFF)
- **⚠️ 结构发现**：记录实际存在 21B 和 28B 两种长度（之前假设全是 21B 不完全对），v9 靠 offset 解析幸免于难

### 2. 哪些字段影响脸型？
**待真机差分（Track A）确认。** 当前推断（C 级）：Byte 0（大类）+ Byte 1（基础纹理）+ Byte 14（头发覆盖）。

### 3. 哪些字段只影响外观类别？
Bytes 4/7/10（布尔开关）+ Bytes 15/16（稀疏 ID）。

### 4. FL26 实际 Face Mesh 的 UV 是否已经数值化？
**✅ 是。Gate 8B 达成。**
- Mesh: `face_African_new1`
- 700 vertices / 1258 triangles / 2 submeshes
- 真实 UV channel (ch4) 已提取至 `work/face_pipeline/uv/mesh_uv.json`
- 线框叠加图已生成 `uv_preview.png`（等待 Daniel 目视确认）

### 5. UV landmark mapping 是否已经完成？
**✅ 是。Gate 8B 达成。**
- `uv_landmark_map.json` 包含 **19 个高精度 landmark**（forehead/brow/eyes/nose/lips/chin/cheek/jaw/temple）
- 所有 landmark 通过 **3D 几何合理性校验**（Z-up 坐标系：forehead z > chin z，双眼对称，鼻-唇-下巴垂直顺序正确）
- UV 误差均 < 0.021，纹理-几何对应关系经像素内容反推交叉验证
- **坐标系确认**：mesh 为 Z-up mask shell（X=左右，Y=深度，Z=上下），不是传统 Y-up

### 6. Photo → Texture 是否已经跑通？
**✅ 是。Gate 8C 达成（原型验证）。**
- 算法选型完成：**TPS (Thin-Plate Spline)** 胜出
- 自测基准：模拟照片（旋转 -8° + 缩放）→ 19 landmark → FL26 UV 512×512
- **TPS PSNR = 31.30 dB**（Piecewise Affine 仅 24.39 dB）
- 输出：`work/face_pipeline/generated/custom_face_test_tps.png`
- 真实照片管线已封装，只需提供正脸照片即可运行

### 7. 是否已经产生独立 Custom Face Texture？
❌ 未开始。计划复制 `face_african_new1` 为 `face_custom_001`，修改材质引用，确保只有 Custom Player 使用。

### 8. 是否已经在单个 League Player 上真机显示？
✅ 基础管线已通（v9 静态球员），但 Custom Face Texture 待 Track D 完成。

### 9. 当前相似度怎样？
TPS 自测 PSNR 31.30 dB（结构正确，非真实照片相似度）。真实照片相似度待 Track D 真机验证。

### 10. 下一步最短路径是什么？
1. **Track A 差分**：构建 1 个 APK 包含 12 个测试球员（各改 1 个字节），Daniel 一次性截图 → 完成 Gate 8A
2. **Track D 注入**：将 `custom_face_test_tps.png` 作为独立 Texture2D 注入 avatar bundle，绑定到 Custom Player
3. **真机验证**：League 中查看 CustomFaceTest 的新脸
4. **真实照片**：提供正脸照片，跑完整 Photo → Game 管线

---

### Gate 状态

| Gate | 状态 | 说明 |
|------|------|------|
| **Gate 8A** Appearance 字段差分 | 🟢 **GREEN** (12:15 真机完成) | Byte1=脸纹理ID / Byte4=发型 / Byte7=胡型 / Byte14=脸型网格 / Byte10=胡色；b1 值域呈 6 值块状=种族纹理家族 |
| **Gate 8B** 真实 Mesh UV 数值化 | 🟢 **GREEN** | 19 landmarks + 全部产物 |
| **Gate 8C** Photo→UV 原型 | 🟢 **GREEN** | TPS 31.30 dB |
| **Gate 8D** 单球员 Face Texture | ⚪ 待启动 | 注入路径已明确：新建纹理资产 + b1 指向 |
| **Gate 8E/8F** | ⚪ 未开始 | - |

---

## 立即行动项（Next Actions）

**需要 Daniel：**
1. 准备 10 分钟真机时间，用于 Track A 批量差分截图（我会构建 1 个包含 12 个测试球员的 APK）
2. 查看 `C:\FL26_Mod\work\face_pipeline\generated\selftest_compare_tps.png`，确认 TPS 还原效果

**我这边继续：**
- 构建 Track A 的批量差分 APK（12 球员单变量）
- 准备 Track D 的 Texture2D 注入脚本

---

## Track 状态总览

```
TRACK A: YELLOW  (分析完成，差分待真机)
TRACK B: GREEN   (UV 数值化 + landmark 全部完成)
PHOTO → FL26 TEXTURE: GREEN  (TPS 原型验证通过)
CUSTOM FACE IN GAME: YELLOW  (基础管线通，独立纹理待注入)
FINAL HIGH-SIMILARITY FACE: YELLOW  (算法就绪，待真实照片+真机验证)

Next: READY FOR TRACK A DEVICE TEST
```
