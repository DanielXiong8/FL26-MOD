# PHASE 13B — Game-Equivalent Appearance Mapping Report

日期：2026-09-07
状态：**APPEARANCE_MAPPING_READY（静态部分）= DONE；五个 PREVIEW_VALID gate = PENDING（等真机 A/B 截图）**
工作区：`D:\FL26_Mod\work\face_pipeline\phase13b\`
受保护资产：未触碰（本阶段全部为只读分析 + 新文件产出；gamedata 写出均为新文件名）

---

## 0. 一句话结论

**外观的"字节 → 资源 → 渲染"因果链已基本解码完毕**（4 张游戏自带映射表 + 头网格双 submesh 结构 + 胡须纯贴图合成实锤），Reference Player 路线被证实为游戏原生做法。剩余不确定性（b3→具体发型网格名、b6>11、b9/b10/b15/b16、虹膜选择字节）已全部转成**可一次真机 A/B 判定的探针矩阵**，APK 已构建签名待设备上线安装。

---

## A. b4 的真实资源映射 — **已解码**

b4 不是发型索引（全库只有 0/127 两个值），是**开关标志**：

- `b4=0`：显式发型生效，配合 `b3`（发型网格索引，观察值 1–84）+ `b5`（发色 id，0–9）
- `b4=127`：哨兵值"默认"——发型由游戏内部规则决定
- **统计学证据**：全库 52,640 人中 b3=255 ⟺ b4=127（47,554 人），b3≠255 ⟺ b4=0（5,086 人），零例外

真实资源链（显式路径）：
```
b4=0 → b3 → 发型网格（SkinnedMeshRenderer，运行时挂头骨，bundle 内 252 个 hair mesh / 178 命名样式）
     → b5 → hairColorConfig[id] mainColor/darkColor + hairSpecColorConfig specColor（直接上色）
```

b3→具体网格名的映射不在任何数据表里（在 IL2CPP 内部列表），**探针 P13B_P01/02/03（b3=1/2/3）真机截图后与 bundle 内候选网格渲染比对锁定**。

## B. b7 的真实资源映射 — **已解码**

b7 同样是开关：`0`=显式胡须（用 b8），`127`=无胡须。

- `b8` → `beardEyebrow` 数据表的 `Beard{b8}` 条目（表内有 Beard1..Beard22，现役库用到 1–7）
- 每条 = `beardEyebrow_atlas_0.png` 的像素 rect（6×i32）+ UV rect（4×f32）
- **实锤：bundle 内不存在任何胡须网格/GameObject——胡须是运行时把图集区域合成到脸纹理上的**（这解释了为什么 b7/b8 在真机有效果但 PC 端看不到）

## C. b10 的真实语义 — **旧描述"胡色"是错的，已纠正**

- 全库 b10 只有 0 和 7 两个值（51,722 人 =0；918 人 =7）
- 918 个 b10=7 的球员**全部是生成假人**（假英文名、b1∈1-9 特殊纹理段、b14=0）
- 结论：b10 是某个**标志位**（值 7），不是胡色、不是虹膜色。对正常球员无可见作用
- 探针 P13B_P17（b10=7）将做最终 null-effect 确认

## D. b14 的真实映射 — **已解码（表格字节级）**

b14 = **FaceTemplate 表索引**（脸型模板）：

- FaceTemplate TextAsset = 140 个模板块；每块 = `u16 模板id + u32 53 + 53 字节 blendshape 权重（0-100）`
- 文件头 7 个 id（7,2,4,6,1,5,3）= 各肤色（b0 1–7）的默认模板
- 全库 b14 观察值 0–139 共 100 个（255=哨兵）；Yang J.=17
- 视觉效果（模板 0/42/99 的脸型差异幅度）由探针 P13B_P12/13/14 真机确认

## E. eye 的真实渲染方式 — **已解码，方案 A 启动**

- 头网格 = **双 submesh**：slot0 = 眼球几何 → 材质 `eye`（Legacy Diffuse）/`M_eye`（Standard），`_MainTex` = 虹膜纹理；slot1 = 面部皮肤 → `face`（Bumped Specular，_BumpMap=head_Normal）/`M_head`（Standard），`_MainTex` = 脸纹理（烘焙目标）
- 虹膜纹理 7 色：darkbrown/darkblue/darkgreen/lightbrown/lightblue/lightgreen/grey
- 每个头存在两套材质路径：根级 `['eye','face']` 与 `player_2021_timeline` 下 `['M_eye','M_head']`
- **死眼根因**：我们把照片眼画进了皮肤纹理，而眼球 submesh 仍渲染默认虹膜
- **选定方案 A**：Previewer 重建游戏眼睛材质路径（虹膜纹理→submesh0），PC 与设备共享同一条渲染方程；虹膜选择字节未在任何 PA 字节中出现（PENDING，通用球员默认 darkbrown）

## F. Reference Player 是否可以成为统一入口 — **可以，且是游戏原生做法**

决定性证据：
1. **StarPlayerAppearance 表**（gamedata TextAsset，29 条）：`pid → [head 预制体, hair GO, hair 材质, face 纹理, 显示名]`——持证球星（曼城全员 + Semenyo/Alleyen/Guéhi）完全不走 PA 字节，全部哨兵值，外观由这张表按 pid 直连资源。Bobb/Ortega/Lewis 等 5 人条目为空名 = 回落通用路径
2. 中国队等通用球员走 PA 字节路径
3. 两条路径都被"**克隆一个已验证球员**"统一覆盖——这正是 Phase 11/12 真机验证过的注入公式

Reference Player 清单：`D:\FL26_Mod\work\face_pipeline\phase13b\analysis\reference_players_chn.json`（19 名多样化中国队球员：Wu L./Le L./Wan D.L./Yang J./Wei/Zhu/Bai 等，覆盖不同发型索引/眉型/脸型/发色）+ 29 星级条目在 `mapping_tables_raw.json`

统一状态对象：`D:\FL26_Mod\work\face_pipeline\phase13b\appearance_state.schema.json`（mode=reference_clone / explicit 双模式，Dashboard、Previewer、Injection 三端同源）

## G. PC 与 Android 是否已经一致 — **尚未判定（本阶段核心 gate）**

- 探针 APK 已构建签名：`D:\FL26_Mod\dist\fl26_phase13b_probe.apk`（基于已验证基线 fl26_e2e.apk，仅替换 gamedata；avatar 不动）
- 18 探针 = P13B_P00..P17（pid 175924–175941）注入**中国队 10059**（25→43 人），每个只改一个字节
- P00 = Yang J. 完整克隆（对照组，必须与 Yang J. 视觉一致）
- 设备当前离线；后台 watcher 已挂（每 30s 轮询 `adb devices`，上线即 `install -r -d`）
- **判据（不许"差不多"）**：安装后进中国队阵容逐个截图，与 PC 渲染逐项对照，写 `MATCH=PASS/FAIL`

## H. 当前 GAME_EQUIVALENT_PREVIEW 状态 — **IN_PROGRESS**

| Gate | 状态 | 依据 |
|---|---|---|
| APPEARANCE_MAPPING_READY | **GREEN（静态部分）** | 4 表解码 + 网格/材质结构 + 52,640 人统计 |
| HAIR_PREVIEW_VALID | PENDING | 需探针 P01–P06 真机图 + PC 端 hair 挂载渲染 |
| BEARD_PREVIEW_VALID | PENDING | 需探针 P07–P09 真机图；合成路径已解码 |
| FACE_SHAPE_PREVIEW_VALID | PENDING | 需探针 P12–P14 真机图 + FaceTemplate 权重应用 |
| EYE_PREVIEW_VALID | PENDING | 方案 A（虹膜 submesh 复现）待 Previewer 实现 |
| PC_ANDROID_APPEARANCE_MATCH | PENDING | 探针 APK 安装后逐项对照 |

## I. 是否具备开始 Browser Face Builder 的条件 — **还不具备，且距离明确**

缺的三件事（全部已在轨道上）：
1. 真机 A/B 判定（探针 APK 就绪，等设备）
2. PC Previewer 升级：加载 hair GO + 双 submesh 材质 + FaceTemplate blendshape（Option B 预加载+热替换路线，未动 WebGL）
3. 虹膜选择字节（若探针证明默认虹膜即可满足一致性，则此项自动关闭）

---

## 附：本阶段新增文件（全部为新建，未修改任何受保护资产）

| 文件 | 用途 |
|---|---|
| `D:\FL26_Mod\work\face_pipeline\phase13b\appearance_mapping.json` | 解码后的完整映射（含证据等级） |
| `D:\FL26_Mod\work\face_pipeline\phase13b\appearance_state.schema.json` | 统一外观状态 schema |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\dump_bundle_structure.py` | bundle 结构分析脚本 |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\dump_appearance_stats.py` | 全库统计脚本 |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\bundle_gos.json / bundle_heads.json / bundle_materials.json` | 4,116 GO / 431 材质结构档案 |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\appearance_stats.json / players_pa_full.csv` | 52,640 人字节级档案 |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\mapping_tables_raw.json` | 4 张映射表原始字节 |
| `D:\FL26_Mod\work\face_pipeline\phase13b\analysis\reference_players_chn.json` | 19 名 Reference Player |
| `D:\FL26_Mod\work\face_pipeline\phase13b\scripts\inject_probe_matrix.py` | 探针注入器（复用已验证注入模式） |
| `D:\FL26_Mod\dist\fl26_phase13b_probe.apk` | 探针 APK（已签名待安装） |
| `D:\FL26_Mod\recon\baselines\APPEARANCE_REGRESSION\` | 回归集目录（探针 manifest + 截图位） |
