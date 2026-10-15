# Appearance 字段语义（Step 8 Track A 结论）

> 依据：12 个单变量真机差分（appearance_diff_v1.apk，London Red，基线=Ralla 克隆）
> + 全量 52,646 条记录熵分析 + 76 个姓名-纹理 token 匹配 + 国籍关联统计
> 日期：2026-09-01

## 最终答案

```text
Byte 0  → 非种族字段。值 2 使肖像朝向翻转（右→左），值 3 无变化。疑似渲染/镜像标志。种族无关。【YELLOW】
Byte 1  → ✅ FACE_TEXTURE_ID（脸纹理 ID）。30→31 肤色略黑、30→32 肤色变白 = 纹理资产切换。【GREEN】
Byte 4  → ✅ HAIR_STYLE（发型/发量）。0=寸头(基线), 1=长发, 127=中等发量。【GREEN】
Byte 7  → ✅ BEARD_STYLE（胡型）。0=络腮胡(基线), 1=下巴一撮, 127=无胡(附带肖像翻转)。【GREEN】
Byte 10 → 胡色 + 渲染细节。0→7 = 胡子黑→棕；0→1 = 肖像翻转+眼型变化。【GREEN/YELLOW】
Byte 14 → ✅ FACE_SHAPE_MESH（脸型网格 ID）。42→43 椭圆→稍尖，42→44 额头更高。【GREEN】
```

## 关键确认

### FACE_TEXTURE_FIELD = Byte 1（GREEN）
**值域结构：每 6 个连续值 = 一个种族脸纹理家族**（与 avatar 包中 7 个通用家族 × 6 变体完全吻合）：

| b1 区间 | 纹理家族 | 证据 |
|---------|----------|------|
| 28–33 | face_southeuropean_new1–6 | nat=2(西班牙) 占主导（272-296人）；Ralla(西班牙)=30 → southeuropean_new3；真机 31/32 肤色变化 ✓ |
| 40–45 | face_SouthAmerican_new1–6 | face_Gonzalez 匹配球员集中 b1=40-45（拉美姓氏） |
| 16–21 | face_african_new1–6 | nat=62 占主导（123-128人） |
| 22–27 | face_eastAsia_new1–6 | b1=25 ↔ face_son_heung_min（孙兴慜，韩国）；nat 43/133/60 = 亚洲国家 |
| 10–15 | face_America_new1–6 | b1=11 ↔ face_young_messi?; nat 29/27 双主导 |
| 34–39 | face_northeuropean_new1–6 | 推断（对称块结构）【C级】 |
| 4–9 | face_southAsia_new1–6 | 推断（对称块结构）【C级】 |
| 1–3 及其他 | 球星专属纹理（face_Haaland, face_Mbappe, face_messi, face_c_Ronaldo…） | b1=25 ↔ son_heung_min 等 token 匹配 |

> **种族由此控制**：Daniel 观察"12 个测试全是西班牙裔感觉" ✓ 与基线 b1=30 (southeuropean) 一致。
> **要非洲脸 → b1=16..21；东亚脸 → b1=22..27**（无需改 b0）。

### HAIR_FIELD = Byte 4（GREEN）
| 值 | 效果 | 来源 |
|----|------|------|
| 0 | 寸头（基线/Ralla） | 真机 |
| 1 | 长发 | 真机 T05 |
| 127 | 中等发量 | 真机 T06 |
| 其余（熵分析 11 个唯一值） | 其他发型 | 未测 |

### FACE_TYPE_FIELD = Byte 14（GREEN）
脸型网格 ID：42=椭圆(基线), 43=稍尖, 44=高额头。全量值域 100 个唯一值（37-41 最常见），可能直接索引 avatar 包中的 face_*_new1-6 系列网格。

### SKIN_FIELD
无独立肤色字节——**肤色由 Byte 1 的纹理家族决定**（同家族 6 变体自带深浅差异）。

## 产物
- `appearance_diff/baseline.json + T01..T12.json`：实验记录（baseline/modified bytes）
- `appearance_diff/appearance_diff_results.csv`：真机观察汇总
- `face_texture_registry.csv`：76 个姓名-纹理匹配（含 b1/b4/b7/b10/b14 全字段快照）
- `hair_registry.csv`：发型 ID 真机实测（3 个值，其余待按需补充）

## 附注
- Byte 4/7 在全量数据中仅观测到 {0,127}，但值 1 仍然生效（长发/下巴一撮胡）→ 枚举比数据中出现的更宽，未来可按需取值
- T08 (b7=127) 的肖像翻转与 T01/T09 的翻转现象疑似同源渲染标志（C级）
- 28B 记录变体：7 字节扩展语义未研究（超出本阶段范围）
