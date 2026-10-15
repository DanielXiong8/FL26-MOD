# OPENCLAW_FL26_HANDOVER.md — OpenClaw → Zcode FL26 知识移交

> 生成：2026-09-05。**本文件为 Zcode 对 OpenClaw 记忆的只读学习记录。**
> OpenClaw workspace（`C:\Users\Lenovo\.openclaw\`）全程未做任何修改。
> 路径约定：`LEGACY_ROOT = C:\FL26_Mod`（历史，仅存在于 OpenClaw 记忆中）；
> `CURRENT_ROOT = D:\FL26_Mod`（当前实际项目，2026-09-04 迁移，SHA256 已验证一致）。

## 0. OpenClaw 环境定位（实测）

| 项 | 位置 |
|---|---|
| OpenClaw 根目录 | `C:\Users\Lenovo\.openclaw\` |
| workspace 根目录 | `C:\Users\Lenovo\.openclaw\workspace\` |
| 每日记忆（FL26 知识所在） | `C:\Users\Lenovo\.openclaw\workspace\memory\2026-08-31.md` … `2026-09-03.md` |
| Tier-1 永久记忆 | `C:\Users\Lenovo\.openclaw\workspace\MEMORY.md`（**FL26 提及数 = 0**，主体是 ALS 研究项目） |
| FL26 相关 skill | 无专门 skill；`plugin-skills\`（browser/qqbot 等）与 FL26 无关 |
| 历史会话转录 | `C:\Users\Lenovo\.openclaw\agents\main\sessions\*.jsonl`（含 FL26 字样，未挖掘，只读保留） |
| memory\ 根目录 | 仅一个已迁移的 `main.sqlite.migrated`（2026-08-08，非现行格式） |

FL26 在 OpenClaw 中是**日记级（Tier-2 每日记忆）**知识，未固化进 Tier-1 永久记忆。
FL26 相关记忆文件：`2026-08-31.md`（项目状态审计）、`2026-08-31-step3b.md`（Save Editor）、
`2026-09-01.md`（Step 8 Track A + MICA 决策）、`2026-09-02.md`（MICA 渲染确认/模型决策）、
`2026-09-03.md`（bake8/allchina/v5c 裁决/Candidate Pool v1，当天记忆止于 16:40）。
9/4-9/5 记忆属于另一项目（ALS/KG），与 FL26 无关。

---

## A. OpenClaw 已确认事实（明确验证过的结果）

### A1. APK / 构建链路
- 原包工作副本 `working\base.apk`（395,361,449 B，Gate 2A 2026-08-31 校验 SHA256 `8D567E06…C6C3B`，与 D 盘现状一致）。
- 签名链路全通：zipalign -p -f 4 → apksigner（自签 `build\fl26_test.keystore` RSA2048/SHA384）→ verify v1+v2+v3（Gate 2C PASS）。
- `adb install` 在真机（设备 95e2d9a）多次 Success（9/3 多轮 APK 安装）。
- **MIUI HyperOS 教训**：install 时剥离 debuggable flag（即使 manifest 有）；`adb backup` 产生空文件。→ 依靠 SaveExport/SaveImport Activity（Java 级）做存档进出。

### A2. 存档 / 球员数据（Step 3B，10/10 Gate PASS，真机验证）
- 存档 SQLite 4 表：archive_blob(1)/match_blob(1107)/player_blob(37616)/team_blob(1507)；player_blob PK=(data_scope,player_id)，payload=protobuf。
- protobuf 结构：f1=pid, f4=pos, f5=team, f8=jersey, f9.details{name,birth,height,f4-f20=**17属性**,f21=overall,f22=foot}；archive_blob.f8.f22=user_team_id。
- UserPlayer = player_id=1（向导覆盖 Christopher Bailey，kit "BAILEY" #13）。
- CLI 存档编辑器 `tools\custom_player_editor\`（editor.py / protobuf_editor.py / sqlite_store.py）。
- 17 属性修改 + 重启持久化均已真机确认（**仅 PlayerCareer 存档语义**）。
- 工程教训：protobuf string 误判 nested message → 必须 roundtrip 验证；AXML 插 Activity 时 csize=8+body。

### A3. 外观字段语义（Step 8 Track A，12 项真机差分，Gate 8A/8B/8C GREEN）
- **Byte1 = FACE_TEXTURE_ID**（6 值一块=种族纹理家族）：16-21=african、22-27=eastAsia、28-33=southeuropean、40-45=SouthAmerican、10-15=America、34-39=northeuropean、4-9=southAsia、1-3=球星专属；**b0 与种族无关**。
- Byte4=发型（0寸头/1长发/127中等，真机 T05/T06 验证）；Byte7=胡型（0络腮/1下巴撮/127无胡）；Byte10=胡色+渲染标志；Byte14=脸型网格（42椭圆/43稍尖/44高额头）。无独立肤色字节。
- 产物：`recon\03_player\appearance_field_semantics.md`、face_texture_registry.csv（76 行）。

### A4. Avatar bundle / Mesh 工程（真机注入管线全通）
- `avatar.unity3d`（67.6MB）：553 Mesh + 754 Texture2D，85 张脸纹理（512×512 RGBA）。
- ea1(eastAsia_new1) 与 se3(southeuropean_new3) 拓扑完全一致（700 顶点/1254 三角形/UV 全同，仅 blendshape 不同）。
- **关键工程知识（OpenClaw 9/3 记忆原样移交）**：
  - UnityPy 1.25.3 改 Mesh：`read_typetree` → 改 dict → `save_typetree`；TextAsset 用 `read(check_read=False)+save()`。
  - 游戏 Mesh stream0 stride=40（pos3+normal3+tangent?+2uv=10 floats/vert），**uv0=stream1 offset0**。
  - m_IndexBuffer uint16（indexFormat 0）；submesh0=眼球(32面)，submesh1=脸(1222面)。
  - **游戏资产 X 轴与提取 JSON 相反（提取时翻转），写回需 x 取反**。
  - PIL transform(AFFINE) 参数是**逆映射**（dst→src），误用正向=黑图。
  - 跨图集采样必须 wrap（UV 环回），PIL 越界填黑。
  - eastAsia 网格家族：new5/6 与 new1 UV 同构（仅顶点序不同）；new2/3/4 独立图集；**new4=698 顶点（拓扑不同）**。
- 探针实验定案：品红纹理+变形网格注入 → 亚洲球队全品红+部分脸变形 → **avatar 注入管线真机全通**。
- **老存档外观冻结**：Ralla 老存档对 b1 换脸无效（外观固化进存档）；PlayerAppearanceTable 只影响新建存档；b4=1 长发对老存档仍生效（字段级差异）。正式路线=改表+新建存档。

### A5. 脸部管线（MICA → fitting → bake → inject）
- 模型决策：**MICA = Identity Reconstruction Backend**（FLAME 网格 5023 顶点/mm/Y-up + identity 332 维 + 68 landmarks，无纹理）；FaceVerse 自带纹理但形状不像（用户判定）→ MICA 几何 + 照片烘焙纹理 = 完整方案。
- Track D 烘焙成果：`baked_111.png`（马健涛照片烘焙）、`baked_ea1/ea2.png`、`bake_mask.npy` 等；纹理烘焙不依赖 MICA 几何（照片→FL26 UV 直接贴）。
- Stage1 相似变换（10 锚点，残差 10.5mm）；Stage2c TPS 14 锚点+falloff（MICA 只盖面部，不整头投影）。
- bake7 坐标系 bug 定案（Z-up 网格被当 x,y 渲染平面）→ bake8 修复（(x,z) 平面+MediaPipe 14 语义锚点 Procrustes+原生 UV 栅格化），眼区倾斜 5.5°→0.8°。
- MICA 顶点注入 5/6 张 eastAsia 网格（new4 跳过），roundtrip 0 误差，真机安装 Success。
- **allchina 路线**（用户转向）：中国队全员马健涛。v4（new2/3/4 用 3D-NN 对应+griddata 重采样进各自图集）→ v5（逐三角仿射光栅化+眼球收缩 15%）→ v5b（wrap 环回修竖黑条）→ **v5c（wrap 双线性+接缝羽化）中线裂缝仍未修好**。

### A6. Candidate Pool Generator v1
- 用户验收标准重定义：照片输入返回 N=8 参数差异候选，≥1 个像+完整即可，坏的剔除。
- `face_benchmark\scripts\generate_candidates.py`（v1 基线零改动）：reg×lmw×align×light 4 维确定性网格，固定 seed，config.json 可复现。
- 指标：tilt/uv_coverage/暗簇对称/seam(p99.5)/feature_consistency/black%%；photo_fidelity=identity 代理（InsightFace 1.0.1+buffalo_l 已装但风格化渲染 0 faces → 按规格降级 UNAVAILABLE）。
- 首轮 test01（照片 photo_111）：6 OK / 2 REJECT(tilt) / 2 DUP；**c4 最优 0.734（fid 0.704）> c7(=v1 参数复刻) 0.590（fid 0.504）** → 参数空间存在明显优于 v1 的区域。
- 产物：`face_benchmark\runs\test01\`（candidates/contact sheets/metrics.csv/report.html/config.json）。

## B. OpenClaw 的当前项目状态（截至记忆终点 2026-09-03 16:40）

- **已完成并真机验证**：APK 管线（2A/2C）、Step 3B 存档编辑（10 Gate）、Step 4A 静态 League 球员注入（新玩家进入 League，姓名/位置/17属性可注入）、Step 8 Track A 外观语义（8A/8B/8C GREEN）、Track D 烘焙、MICA 适配+注入、allchina v1→v5c、Candidate Pool v1。
- **记忆终点时的待裁决**：contact sheet 目视验收（数值上 c4 已最优）； Candidate Pool 待办（seam 列剖面精化、眼指标、候选进 APK 注入对接）。
- **记忆终点后项目文件记录的演进**（Zcode 已从项目文件接管，见 ZCODE_HANDOVER.md）：9/3 晚进入 Step 9 = FL26 PC Avatar Previewer（C 盘时代最后一段工作，PC_PREVIEW_VALID=BLOCKED）；9/4 项目整体 C→D 迁移。
- **Gate 现状**（项目文件为准）：Step 9 全部 7 项 BLOCKED（Unity 2020.3.49f1 未安装）。

## C. OpenClaw 的冻结决策（必须尊重，不得擅自重启）

| 决策 | 内容 | 依据 |
|---|---|---|
| face pipeline v1 | **FROZEN BASELINE**（冻结于 v5b/v5c 状态，allchina 路线） | 用户裁决 2026-09-03 15:54 |
| v5c 中线裂缝 | **归档，不再追修**（"已有足够多像马健涛的球员"） | 用户裁决 2026-09-03 |
| Python custom renderer | **停止维护**（matplotlib/trimesh/pyglet/自研光栅均不再修；PC 端唯一正路 = Unity Previewer） | 9/1-9/3 记忆 + 项目文件 |
| PlayerCareer 路线 | **暂停**（Step 3B 存档编辑已完成收尾，主线转静态 League 球员） | 8/31 审计后路线选择 |
| 相似度专项 | **已验收通过**，不再作为瓶颈 | 9/3 记忆 |
| 当前主线 | **Step 9 — FL26 PC Avatar Previewer** | 项目文件（9/3 晚起） |

## D. OpenClaw 尚未验证的事情（推测不算事实）

1. **记忆断档**：9/3 16:40 后的工作（PC Previewer 设计、静态检查、Unity 首次尝试）无 OpenClaw 记忆条目——此段以项目文件为唯一事实来源。
2. contact sheet 用户目视裁决无记录条目（项目文件后续直接以 c4 为当前候选，视为事实接受，但无明确 GREEN 记录）。
3. b7=1 山羊胡未出的依赖机制（是否依赖 b10）未查清。
4. 静态 League 球员 17 属性的真机验证（modify_bundle.py 接 APK 管线）未完成。
5. Candidate Pool seam 指标列剖面法精化、眼指标（眼窝洞问题）未完成。
6. Wu L./Wei/Liu D. 的 head GameObject 名未从 bundle 枚举（Previewer 首跑后可解决）。
7. 老/新存档外观读取差异的完整机制（为何 b4 生效而 b1 不生效）未定论。
8. Unity 2020.3.49f1 在本机的安装与许可激活状态（截至接管时未安装）。

## E. OpenClaw 使用过的关键路径（**历史路径，不得当作当前路径**）

> `LEGACY_ROOT = C:\FL26_Mod\` — 以下全部为 LEGACY_ROOT 下的历史记录；对应内容现位于 `D:\FL26_Mod\` 下相同相对位置。

| 历史路径（LEGACY_ROOT 相对） | 内容 |
|---|---|
| `working\base.apk` | pristine 原包工作副本 |
| `build\` | 全部构建产物 + `fl26_test.keystore` |
| `face_benchmark\scripts\track_d_bake*.py` | bake 迭代链（bake8 为最终修复版） |
| `face_benchmark\work\face_pipeline\track_d\` | baked_111.png / baked_ea1-3.png / bake_mask.npy / ea3_remap_newX.png |
| `face_benchmark\adapter\` | MICA 适配产物 fl26_ea1_adapted.obj / overlay3.png / benchmark_report.md |
| `face_benchmark\runs\test01\` | Candidate Pool v1 首轮产物（c4 等） |
| `outputs\mica\test0{1-3}_front\` | MICA 原始输出 |
| `recon\03_player\appearance_field_semantics.md` | 外观字段语义定论 |
| `recon\reports\` | 全部阶段报告 |
| `tools\custom_player_editor\` / `tools\saveexport\` | 存档编辑器 / SaveExport Activity |

**路径原则**：OpenClaw 记忆中的 `C:\FL26_Mod` 仅提供历史上下文；一切实际工作以
`CURRENT_ROOT = D:\FL26_Mod` 文件系统实测为准（本次接管已实测确认，SHA256 4/4 一致）。
