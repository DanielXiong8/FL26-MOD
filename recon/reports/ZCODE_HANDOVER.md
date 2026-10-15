# ZCODE_HANDOVER.md — Zcode 接管记录

> 生成：2026-09-05。本文件是 Zcode 接管 FL26_Mod 的权威记录。
> 姊妹文件：`OPENCLAW_FL26_HANDOVER.md`（OpenClaw 知识移交）、`HANDOVER_CONFLICTS.md`（冲突检查）、
> `PATH_MIGRATION_AUDIT.md`（C→D 迁移审计）、`..\handover\handover_manifest.json`（备份基线）。

## 1. SOURCE_OF_TRUTH 声明

**SOURCE_OF_TRUTH = CURRENT PROJECT FILES + VERIFIED REPORTS（`D:\FL26_Mod` 下经校验的文件与报告）**

- OpenClaw memory（`C:\Users\Lenovo\.openclaw\workspace\memory\`）仅作为**历史上下文**，单独不构成事实来源。
- 二者不一致时：以当前实际文件 + 最新验证结果为准，并在 `HANDOVER_CONFLICTS.md` 记录（不自动覆盖任何一边）。
- 路径：`LEGACY_ROOT = C:\FL26_Mod`（历史）；`CURRENT_ROOT = PROJECT_ROOT = D:\FL26_Mod`（当前）。

## 2. 项目根目录

`D:\FL26_Mod`（2026-09-04 从 `C:\FL26_Mod` 迁移；SHA256 4/4 基线一致，详见 PATH_MIGRATION_AUDIT.md）。
运行时代码不写死盘符：`FL26_PROJECT_ROOT` 环境变量覆盖 + 向上自动发现（见 PreviewerBootstrap.cs）。

## 3. OpenClaw 环境（只读，未修改）

- 根目录：`C:\Users\Lenovo\.openclaw\`
- workspace：`C:\Users\Lenovo\.openclaw\workspace\`
- FL26 知识：`workspace\memory\2026-08-31.md` / `2026-08-31-step3b.md` / `2026-09-01.md` / `2026-09-02.md` / `2026-09-03.md`
- Tier-1 `MEMORY.md`：FL26 提及数 = 0（FL26 是日记级知识，非永久记忆）
- 接管会话期间对 OpenClaw 的写入操作：**零**

## 4. 当前 FL26 project state（截至 2026-09-05）

| 阶段 | 状态 |
|---|---|
| Step 2 APK 管线（解析/重签/真机安装） | ✅ 完成（Gate 2A/2C PASS） |
| Step 3A/3B 存档编辑（PlayerCareer） | ✅ 完成（10/10 Gate PASS），路线已暂停 |
| Step 4A 静态 League 球员注入 | ✅ 打通（新玩家进 League；姓名/位置/17属性可注入） |
| Step 8 外观语义 + 脸部 recon（MICA） | ✅ 完成（8A/8B/8C GREEN；MICA 为几何后端） |
| 换脸管线 v1（allchina）→ v5c | ✅ 完成并**冻结**（v5c 归档，不再追修） |
| Candidate Pool Generator v1 | ✅ 完成（test01 首轮：c4 最优 0.734 / fid 0.704） |
| **Step 9 PC Avatar Previewer** | 🔶 **当前主线**，7/7 Gate BLOCKED（Unity 缺席） |

## 5. 当前 Step 与 Gate

- 当前 Step：**Step 9 — FL26 PC Avatar Previewer**
- `PC_PREVIEW_VALID = BLOCKED`
- 全部 Gate：STEP9_ENGINE_READY / ASSET_LOAD / RENDER / UV / SHADER / CANDIDATE 均 BLOCKED
- 唯一根因：**Unity 2020.3.49f1 未安装**（本机仅 2020.3.9f1c1 @ `D:\Unity\Editor`、Tuanjie 2022.3.62t14 @ `D:\2022.3.62t14`）

## 6. 工具链

| 工具 | 状态/位置 |
|---|---|
| Java | ✅ JDK 21.0.12（Microsoft，JAVA_HOME 已设） |
| adb | ✅ `D:\FL26_Mod\android-sdk\platform-tools\adb.exe` |
| apksigner / zipalign | ✅ `D:\FL26_Mod\android-sdk\build-tools\36.0.0\` |
| Python | ✅ 3.13.14（系统）+ `face_benchmark\envs\envs\recon`（项目 env） |
| Unity Hub | ✅ `C:\Program Files\Unity Hub\Unity Hub.exe`（secondaryInstallPath=D:\） |
| Unity Editor 2020.3.49f1 | ❌ 未安装 |

## 7. 原始资产 SHA256（迁移后复验，全部一致）

| 文件 | SHA256 |
|---|---|
| `working\base.apk` | `8D567E06D93D30924741D2A4F439D1E81E062D9AEB8F203FCE64E7437A0C6C3B` |
| `build\pristine_resigned.apk` | `2C4F3048E2238D0622C42A2E838945E996861F54035C49196BDFB49118878723` |
| `build\avatar.unity3d` | `41567C9AC5B3A71116776CB566CBB49774BEEEB6C4BD3471E619F7734F22D5B7` |
| `build\gamedata.unity3d` | `12438AB78124BB026FF81055DDAFB1C8DA97EF0DDCC436188E881359FB38A235` |

冻结产物基线（v5c）：`build\avatar_ea3_v5.unity3d` = `dc7af4e9…9630`；`dist\fl26_allchina_v5.apk` = `77c825ec…8391`。

## 8. 当前 APK build 状态

- 最后真机安装版本：`fl26_allchina_v5.apk`（v5c，2026-09-03）；历史各版本 APK/Bundle 全部保留于 `build\` / `dist\` / `modified\`，未清理。
- 签名密钥：`build\fl26_test.keystore`（自签测试证书）。
- 构建脚本链完整保留于 `scripts\`（build_*.py/.ps1，含旧 C: 路径，重跑前需单点替换，见 PATH_MIGRATION_AUDIT.md 4.3）。

## 9. 当前 face pipeline 状态

- v1 基线（allchina）：**冻结**。脚本 `face_benchmark\scripts\`（track_d_bake8 为最终修复版）+ `tools\custom_player_builder\`。
- Candidate Pool v1：`face_benchmark\scripts\generate_candidates.py`；产物 `face_benchmark\runs\test01\`（c4 为当前候选）。
- MICA 适配产物：`face_benchmark\adapter\`（fl26_ea1_adapted.obj 等）。
- 已知残留（归档不追）：v5c 中线裂缝；b7=1 山羊胡未出；静态球员 17 属性真机验证未做。

## 10. 当前 Previewer 状态

- 工程：`D:\FL26_Mod\tools\FL26_AvatarPreviewer\`（单文件入口 PreviewerBootstrap.cs，无场景资产，Built-in RP）。
- ProjectVersion.txt = 2020.3.49f1（2026-09-05 修复，此前被 2020.3.9f1c1 batchmode 覆写）。
- 无预置 ProjectSettings.asset（等 2020.3.49f1 首开自生成）；manifest.json 极简 builtin。
- 路径策略：`FL26_PROJECT_ROOT` 环境变量覆盖 + 自动发现 PROJECT_ROOT；输出 `tools\FL26_AvatarPreviewer\runs\preview\`。
- 从未成功导入运行（无 Library\）；c4 过渡预览 `face_benchmark\runs\test01\candidates\c4\front.png` 仍为唯一有效 PC 预览。

## 11. 回退机制（可回到 OpenClaw）

- OpenClaw workspace/memory/config：**未做任何修改**（本接管全程只读）。
- 接管前备份：`D:\FL26_Mod\recon\handover\pre_handover_backup\`（~13MB：Previewer 工程全量、recon\reports、scripts、face_benchmark\scripts、custom_player_builder/editor、saveexport、test01 关键文件）。
- 大文件以 SHA256 记录（handover_manifest.json），未复制多份。
- 项目无 Git；无 destructive git 操作风险。
- **Zcode 行为约束**（生效中）：不删除旧版本/唯一副本；不把 Zcode 专属路径写死进项目；新脚本放项目自有目录；新实验用独立 run 目录；OpenClaw 可随时在原状态上继续。
