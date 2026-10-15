# PC_AVATAR_PREVIEWER_REPORT.md

> Step 9 最终报告（2026-09-03 22:35）。SETUP 操作手册见 `PC_AVATAR_PREVIEWER_SETUP.md`，状态清单见 `PC_AVATAR_PREVIEWER_STATUS.json`。

## 1. 回答 19 项最终问题

| # | 问题 | 答案 |
|---|------|------|
| 1 | 真实 FL26 Mesh 加载？ | **BLOCKED**（代码就绪，需 Unity Editor 验证） |
| 2 | 真实 FL26 Material 加载？ | **BLOCKED**（同上） |
| 3 | 真实 FL26 Shader 加载？ | **BLOCKED**（已内置 InternalErrorShader 检测，能否原生运行需实测） |
| 4 | UV tile 复现？ | **BLOCKED**（正确路径=引擎原生采样；不再手写复现） |
| 5 | Repeat/Clamp 复现？ | **BLOCKED**（同上；脚本会自动 dump 实际 wrapMode） |
| 6 | new1-new4 正确？ | **BLOCKED**（Play 后按 N 逐一目视） |
| 7 | PC ≈ Android？ | **BLOCKED**（9G，需截图对比） |
| 8 | c4 在 Viewer 查看？ | **BLOCKED**（按 C 即载入 `c4/baked.png`） |
| 9 | 候选池直接接入？ | **是**（`candidateTextureCandidates` 数组即可批量挂候选） |

## 2. 已完成（不依赖 Unity 也能确认）

1. **工程最小闭环**：`Assets/Scripts/Runtime/PreviewerBootstrap.cs`（单文件，无场景依赖，`RuntimeInitializeOnLoadMethod` 自动启动）
   - AssetBundle.LoadFromFile 只读加载原始 `avatar.unity3d`（2020.3 API，无 UnityWebRequest/UGUI 依赖）
   - 全资产枚举 → `runs/preview/asset_enumeration.txt`
   - 逐 Avatar 依赖 dump（Mesh/SMR/Material/Shader/Texture/_MainTex 槽/bones）→ `runs/preview/deps_*.txt`
   - GameObject 加载失败自动降级 Mesh+Unlit/Texture fallback（可验证几何/UV，同时记录 SHADER_FALLBACK）
   - 左键旋转/滚轮缩放/1234 固定视角/N 换脸/C 载入候选/P 截图 → `runs/preview/*.png`
2. **ProjectVersion.txt = 2020.3.49f1**；刻意不预置 ProjectSettings.asset（Unity 首开自动生成，避免手写 YAML 损坏工程）
3. **manifest.json 极简**：仅 builtin 模块，无 URP/HDRP/第三方
4. **静态自检全绿**：3 个 JSON 可解析、C# 括号平衡、无高版本 API、原始资产 SHA256 基线已记录：
   - `avatar.unity3d` = 41567C9A…D5B7
   - `gamedata.unity3d` = 12438AB7…A235
   - `pristine_resigned.apk` = 2C4F3048…8723
5. 清理：删除无效的手写 ProjectSettings.asset、旧版 AvatarPreviewer.cs、残留的 matplotlib/trimesh 脚本

## 3. BLOCKED 项（唯一根因：Unity 2020.3.49f1 未安装）

- 9A/9B/9C/9D/9E/9F/9G 全部 BLOCKED
- Wu L. / Wei / Liu D. 具体 head GameObject 名：BLOCKED（首次运行后从 `asset_enumeration.txt` 读取）
- per-Avatar 完整依赖表：BLOCKED（运行时自动生成，不伪造）

## 4. 安装后第一轮验证命令（人工操作序列）

1. Unity Hub → Open → `C:\FL26_Mod\tools\FL26_AvatarPreviewer`（用 2020.3.49f1 打开）
2. New Scene (Empty) → Play ▶
3. 检查 `runs\preview\load_state.txt`：`bundleLoaded=True` = 9B
4. Game 视图目视 new1 → `1`+`P` 截图
5. `N`×3 看 new2-4（重点：不再是碎块 = 9E）
6. `C` 载入 c4 → `1..4`+`P` 四角度 → 9F
7. `runs\preview\*.png` vs Android 截图 → 9G 裁决

## 5. 红线遵守

- 原始 avatar.unity3d / base*.apk 只读（SHA256 基线可复验）
- 未修 v5c，未动 face pipeline v1
- 过渡有效结论保留：`runs/test01/candidates/c4/front.png` 仍是当前唯一有效 PC 过渡预览

## PC_PREVIEW_VALID = BLOCKED

---

# 6. C→D 迁移接管审计（2026-09-05 追加，历史内容未改动）

> 详细审计见 `PATH_MIGRATION_AUDIT.md`；状态机见 `PC_AVATAR_PREVIEWER_STATUS.json`（已更新）。

- **PROJECT_ROOT = `D:\FL26_Mod`**（`D:\FC26Mod` 不存在，已实测确认）。
- **迁移完整性 PASS**：4/4 基线 SHA256 与迁移前一致（`working\base.apk` = Gate 2A 基线、`pristine_resigned.apk`、`avatar.unity3d`、`gamedata.unity3d`）——内容零变化，仅路径变化。
- **旧路径残留**：全项目 212 个文件仍引用 `C:\FL26_Mod`（历史报告/一次性脚本，按红线不批量改动）；
  4 个**活跃文件**已修复：`PreviewerBootstrap.cs`（硬编码 bundle 路径与 c4 路径 → `FL26_PROJECT_ROOT` 环境变量覆盖 + 向上自动发现 PROJECT_ROOT）、`PC_AVATAR_PREVIEWER_SETUP.md`、`README.md`、`STATUS.json`。
- **发现并修复**：ProjectVersion.txt 曾在 2026-09-03 22:48 被错误版本的 Unity batchmode（2020.3.9f1c1）覆写，已恢复为 `2020.3.49f1 (a8928a80ccc7)`。证据：随项目拷贝的 editor*.log / import.log / manuallic.log（保留未删）。
- **路径解析现在可自证**：Play 后 `runs\preview\load_state.txt` 会写入 `fl26ProjectRoot=` 与 `unityProjectDir=`，Gate 9A 直接可验。
- **Unity 现状**：本机仅有 2020.3.9f1c1（`D:\Unity\Editor`）与团结引擎 2022.3.62t14；**2020.3.49f1 未安装** → 9A-9G 维持 BLOCKED，不代下载。
- Gate 状态：7/7 BLOCKED（无新增 RED；无一条"脚本存在=功能通过"的绿灯）。

## PC_PREVIEW_VALID = BLOCKED（2026-09-05 复核维持）

---

# 7. Step 9 首轮真实验证战报（2026-09-05 追加）

> Gate 状态机已同步更新（STATUS.json）。本轮把 9A-9F 全部从 BLOCKED 推进到 GREEN，PC_PREVIEW_VALID 保持 BLOCKED（9G 待做）。

## 7.1 环境落地

- Unity **2020.3.49f1**（revision `18249dd5551b`，官方 API 实查；SETUP.md 旧记录 `a8928a80ccc7` 为错误 hash 已修正）安装于 `D:\Unity\Editor-2020.3.49f1`，许可激活成功。
- 补装 **Android Build Support** 模块（bundle 为 Android 平台构建，必须以 `-buildTarget Android` 运行）。

## 7.2 攻克的根因链（每一环都有实证）

1. **原始 bundle 无法加载** ≠ 版本问题：序列化版本就是 2020.3.49f1。真因 = 内嵌 442 个游戏 MonoBehaviour/33 个 MonoScript + 序列化头 script_types(33) + types 表(34 条脚本类型条目)。DummyDll 方案（98 个 stub 进 Plugins）证明不够——错误文案 "references scripts not compatible" 是 Unity 的通用兜底话术。
2. **解法 = UnityPy 无脚本重写副本** `extracted/avatar_clean.unity3d`（原包只读不动，SHA256 校验不变）：删 475 个脚本对象 → 清头 script_types → types 表手术（59→25，按引用计数保留 SpriteAtlas 的哈希类型）→ 重建 container/preload 区间（保 new1 的 1167 条资产区间连续）。**探针三角定位证实副本可加载。**
3. **截图全空的真因**（场景审计定位）：head prefab 根节点**默认 inactive**（游戏运行时激活）+ 编辑模式无渲染循环 → SMR boneMatrices 恒为零。修复 = `SetActive(true)` + SMR 静态化（sharedMesh 挂 MeshFilter，按 rootBone 相对变换 re-base；BakeMesh 在零矩阵下无效）。
4. **new1 单独失败**：其资产区间含 1 个 MonoBehaviour+1 个 MonoScript，删除后 LoadAsset 区间解析失败 → 用 `LoadAllAssets<GameObject>()` 按名兜底（对其他 5 脸无损）。
5. 工程修正：manifest 补 `assetbundle`/`imageconversion`/`ugui`；`bundle.isLoaded` 是幻影 API（从未编译过）；引入 asmdef 隔离程序集身份。

## 7.3 验证结果（run42，全程 batchmode 自动化）

| 项 | 结果 |
|---|---|
| bundle 加载 | ✅ bundleLoaded=True |
| 脸加载 | ✅ **6/6**（new1 走 LoadAllAssets 兜底） |
| deps dump | ✅ 6 份（SMR 700vc/698vc、骨骼、材质、原生 shader 全记录） |
| 资产枚举 | ✅ 553 Mesh / 754 Texture2D / 554 GameObject / 438 Material / 23 Shader |
| 原生 shader fallback | ✅ **0** 次 InternalErrorShader |
| c4 候选纹理 | ✅ 加载+应用成功 |
| 截图 | ✅ 13 张（6 脸正面 + new1 三视角 + c4 四视角）`runs/preview/batch_*.png` |
| 目视 | 真实几何+皮肤纹理连续，**无 UV 碎片/黑条/seam**（当前角度为头顶/后脑视角） |

## 7.4 已知残留（下一轮）

1. **取景姿态**：head 顶点在 rootBone 空间（Biped Z-up），当前截图是仰头/后脑视角。需 -90°/180° 组合精调（已在 localRotation 参数化，改一个常数即可），或改相机对 rootBone 姿态对准。
2. **正面特写复核**：9E UV 检查和 9D 原生 shader 光照表现需正面视角二次确认。
3. **9G 真机对比**：PC 渲染 vs Android 游戏内截图——PC_PREVIEW_VALID 的最后一关。
4. 驱动器里的 ForceUnlit 诊断通道保留（排除 shader 干扰用），正式对比时关闭。

## 7.5 取景校正完成（run50，2026-09-05）

- 8 旋转网格搜索定位正确姿态：静态体最终变换 =
  `Euler(0,180,0) * Euler(-90,0,0) * Euler(0,-90,0) * lastRel.rotation * Euler(90,0,0)`（world 前乘 + bone 局部后乘）。
- **正面图确认**（`batch_face_face_EastAsia_new2_front.png`）：绿色虹膜双眼、眉毛、唇部、皮肤明暗全部解剖学正确，UV 连续零碎片。
- **45L 侧脸确认**（`batch_new1_45L.png`）：鼻梁/眉弓/下颌轮廓自然，光照方向正确。
- **c4 应用确认**（`batch_c4_view1.png`）：候选纹理加载应用成功；眼部黄色块 = c4 baked.png 自身的眼锚点烘焙限制（face pipeline 已知问题），非渲染器缺陷。
- 13 张标准角度截图已可用于 9G 真机对比。剩余：9G（需真机）→ PC_PREVIEW_VALID 裁决。

## 7.6 马健涛 mod 脸模上 PC（2026-09-05，run51-59）

**目标达成：PC 端现在能直接看到 allchina v5c mod 的马健涛脸模**（此前只能真机看）。

- 三张源照片定位：`D:\FL26_Mod\face_benchmark\inputs\test01/02/03_front.jpg`（test01 = c4 候选源照片）。
- `make_clean_bundle.py` 参数化后对 **`build\avatar_ea3_v5.unity3d`**（= `dist\fl26_allchina_v5.apk` 打包的 mod bundle）执行无脚本重写 → `extracted\avatar_mjt.unity3d`，并加入 bundleCandidates 首位。
- **贴图实证**：mod bundle 中 `face_southAsia_new1`（6 张东亚脸材质共同引用的 _MainTex）内容已被替换为马健涛照片烘焙纹理（浓眉/暖肤/闭眼照），dump 至 `extracted\mjt_tex\`。
- 渲染：**new2-new6 五张脸在 PC 上正确显示马健涛 mod 脸**（MICA 几何 + 照片烘焙纹理）。
- 已知残留（非 Previewer 缺陷）：① 眼球用原生 eye_darkgreen 贴图（mod 从未替换眼睛贴图，真机亦然）；② 眼球外凸（v5c 已知）；③ **new1 渲染为空**——其 MICA 注入网格的 mesh.bounds 未随顶点重算（stale bounds），AutoFrame 落点错误；修复方向 = 注入脚本写回后重算 bounds，或 Previewer 侧按顶点实际位置取景。

## 7.7 Orbit Capture 定稿（run74-76，2026-09-05）

诊断路径：360° 全景（12 角度 + 参考球）证明头部实际渲染在 renderer.bounds.center、
脸部朝向 pano_180 一侧但上下颠倒。SetFixedView 机位与全景机位存在隐藏差异（连续 8 轮 front 空图）。

**最终方案**：全部截图改用 Orbit 相机（位置+LookAt 绕头部中心，dirDeg=0 为脸侧），
彻底摆脱 SetFixedView/pivot 链。配套修复：
1. MICA 注入网格的 mesh.bounds 按实际顶点重算（stale bounds 修复）；
2. 照片烘焙网格在基础朝向下上下颠倒 → 绕视轴 roll 180 并保持头中心不动（中心保持平移）；
3. new1 走 LoadAllAssets 兜底路径同样适用。

**最终结果：16/16 截图全部有内容**——6 脸 × (正面+背面) + c4 四视角。
正面脸直立、五官位置正确、UV 连续；c4 纹理应用正常（眼区黄块 = c4 烘焙纹理已知限制）。

## 7.8 马健涛 mod 脸模渲染定案（run77-80，2026-09-05）

**用户反馈修正后达成目标：PC 渲染与真机 mod 外观一致。**

### 根因（"不像马健涛"）
bundle 材质只带通用默认贴图 face_southAsia_new1；游戏运行时由 FaceMaterialSupplier
按球员外观动态赋值 face_eastasia_new{fam}（v5c 已替换为马健涛烘焙）。PC 预览缺少这一步。
修复 = 驱动器新增 AssignModFaceTexture（按 v5c 构建脚本的精确容器路径
assets/models/player2021/textures/face/face_eastasia_new{fam}.png 加载并赋给 face 材质；
注意存在 female 同名纹理，不能用文件名映射）。

### v5c 内容实测（解释各脸观感差异）
- **new5/new6**：完整 ea3 照片烘焙直换 → 真机上质量最好的马健涛脸 ✓ PC 渲染一致
- **new2/3/4**：逐三角重映射退化 → 贴图为平滑渐变+接缝线（= 用户冻结的"中线裂缝"问题）→ PC 渲染如实显示
- **new1**：MICA 注入几何 + ea3 直换贴图 → 渲染正常（鼓眼 = v5c 已知残留）
- **眼睛**：全部保持原生 eye_darkgreen（mod 从未替换眼睛贴图，真机相同）

### c4 眼部=鼻子图
c4 baked.png 的眼锚点烘焙缺陷（face pipeline 冻结前已知限制）；c4 从未上过真机
（真机用 ea3 烘焙）。属 face pipeline 问题，非 Previewer 缺陷。

### 真机对照
设备 95e2d9a 在线，mod 游戏（com.football.soccer.league.mod）前台运行
（CHN vs CAM 比赛），device_screen.png 已存档。真机比赛画面中的红衣中国队
即渲染对应的 mod 球员；脸部特写需游戏内导航（待用户配合截取）。

## 7.9 Step 9 收官（2026-09-05 用户裁决）

用户目视 PC 渲染图（16/16 张，6/6 脸）后确认"基本截图可以看出来像马健涛了，这一步可以收尾了"
→ **PC_PREVIEW_VALID = GREEN，Step 9 正式关闭**。

Step 9 最终交付：
- Orbit Capture 批量验证驱动（编辑模式，无 Play/域重载依赖）
- 无脚本 bundle 重写管线（make_clean_bundle.py，参数化）
- FaceMaterialSupplier 运行时行为复刻（mod 贴图赋值）
- 真机对照存档（device_screen.png，CHN vs CAM 比赛中）
