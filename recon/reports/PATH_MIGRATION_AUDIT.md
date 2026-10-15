# PATH_MIGRATION_AUDIT.md — C→D 迁移完整性审计

> 生成时间：2026-09-05（接管审计，只读检查 + 活跃文件最小修复）
> 审计方式：只读扫描 + SHA256 复算；除第 5 节列出的活跃文件外，未修改任何项目内容。

## 1. 当前 PROJECT_ROOT

```
PROJECT_ROOT = D:\FL26_Mod
```

- 默认候选 `D:\FC26Mod\` **不存在**；递归检查 D 盘后确认真实根目录为 `D:\FL26_Mod\`
- 特征齐备：`build\`（avatar.unity3d / gamedata.unity3d / base*.apk / keystore）、`recon\`、`tools\`、`scripts\`、`logs\`、`extracted\`、`modified\`、`dist\`、`face_benchmark\runs\`、`android-sdk\`、`working\base.apk`
- 结构说明：顶层无 `runs\` 目录；runs 位于 `face_benchmark\runs\`（候选池），Previewer 运行时输出到
  `tools\FL26_AvatarPreviewer\runs\preview\`（首次 Play 时生成）——此为原始布局，非迁移丢失。
- `original\` 目录为空（Gate 2A 记录：pristine 原包从未放入 original\，真实 pristine 工作副本为
  `working\base.apk`，已通过 hash 验证，见第 3 节）。

## 2. 迁移完整性结论：**完整，PASS**

- 全部关键目录/文件均在 D 盘存在（见第 1 节）。
- 三个基线资产 + pristine base.apk 的 SHA256 与迁移前记录**完全一致**（见第 3 节）→ 文件内容零变化，仅路径变化。
- 目录 mtime 均为 2026-09-04 09:38（迁移批次时间戳），内部文件 mtime 保留原始时间 → 为整目录拷贝。

## 3. SHA256 基线比对（迁移前记录 vs D 盘实测）

| 文件 | 迁移前基线（2026-09-03 记录） | D 盘实测（2026-09-05） | 结论 |
|---|---|---|---|
| `build\avatar.unity3d` | `41567C9AC5B3A71116776CB566CBB49774BEEEB6C4BD3471E619F7734F22D5B7` | `41567c9a…d5b7` | ✅ MATCH |
| `build\gamedata.unity3d` | `12438AB78124BB026FF81055DDAFB1C8DA97EF0DDCC436188E881359FB38A235` | `12438ab7…a235` | ✅ MATCH |
| `build\pristine_resigned.apk` | `2C4F3048E2238D0622C42A2E838945E996861F54035C49196BDFB49118878723` | `2c4f3048…8723` | ✅ MATCH |
| `working\base.apk`（pristine 原包工作副本） | `8D567E06D93D30924741D2A4F439D1E81E062D9AEB8F203FCE64E7437A0C6C3B`（Gate 2A, 2026-08-31） | `8d567e06…c6c3b` | ✅ MATCH |

**结论：原始资产内容零变化，未触发 STOP 条件，未做任何覆盖/修复/重新生成。**

## 4. 旧 `C:\FL26_Mod` 路径残留扫描

扫描范围：`D:\FL26_Mod` 全部文本类文件（.ps1/.py/.json/.md/.txt/.cs/.bat/.cmd/.yaml/.yml/.sh/.ini/.cfg/.xml/.js/.html），
两种变体（`C:\FL26_Mod` 反斜杠 / `C:/FL26_Mod` 正斜杠）合并去重。

**共 212 个文件仍含旧路径引用**，分类如下：

### 4.1 活跃文件（本次已修复，4 个）

| 文件 | 旧引用 | 处理 |
|---|---|---|
| `tools\FL26_AvatarPreviewer\Assets\Scripts\Runtime\PreviewerBootstrap.cs` | 2 处硬编码（bundle 路径、c4 baked.png） | ✅ 改为动态发现：`FL26_PROJECT_ROOT` 环境变量覆盖 → 从 Unity 工程向上自动寻找含 `build\avatar.unity3d` 的祖先目录；解析结果写入 `load_state.txt` 可验证 |
| `tools\FL26_AvatarPreviewer\PC_AVATAR_PREVIEWER_SETUP.md` | 4 处（工程路径/搜索顺序/c4/输出目录） | ✅ 全部改为 `D:\FL26_Mod` 相对 PROJECT_ROOT 表述，并新增环境变量说明 |
| `tools\FL26_AvatarPreviewer\README.md` | 1 处 + 陈旧的场景/文件描述 | ✅ 路径改为 D 盘；目录结构/使用方式同步为单文件无场景设计 |
| `recon\reports\PC_AVATAR_PREVIEWER_STATUS.json` | baseline 键为 C: 路径、validTransitionalResult 为 C: 路径 | ✅ 键与值更新为 D 盘路径（基线 hash 值不变），并新增 migration 字段 |

### 4.2 历史报告 / 日志（**不应修改**，保留原样）

- `recon\reports\`：`PROJECT_STATE_AUDIT.md`、`STEP_8_FACE_RECON_REPORT.md`、`PC_AVATAR_PREVIEWER_REPORT.md`（第 1-5 节历史记录部分）等 —— 属于当时事实的记录，改写即篡改历史。
- `logs\`：`copy_validation.md`（Gate 2A）、`resign_validation.md`（Gate 2C）—— C 盘时代的验证证据。
- `tools\FL26_AvatarPreviewer\editor*.log`、`import.log`、`manuallic.log` —— 迁移前（9月3日晚）Unity 尝试启动的真实日志，是第 6 节事件的证据，保留。
- `tools\FL26_AvatarPreviewer\PreviewerBootstrap.cs` 内 1 处注释文字提及旧路径（说明"旧硬编码已移除"），为迁移说明性注释，非功能引用。

### 4.3 一次性分析/构建脚本（**不批量修改**，约 180 个）

- `scripts\`（147 个 .py/.ps1）：Step 2-4A/league/clubplayer 等已完成阶段的一次性脚本。属于历史产物；
  若未来需要重跑某个脚本，重跑前将其中 `C:\FL26_Mod` 替换为 `D:\FL26_Mod` 即可。
- `face_benchmark\scripts\`（约 28 个）+ `tools\custom_player_builder\`（约 20 个）：face pipeline v1 / 候选池生成器的
  过程脚本，face pipeline v1 已冻结，同上处理。
- `recon\07_save\sqlite_schema.md`：历史 schema 文档。

### 4.4 环境生成物（不修改）

- `face_benchmark\envs\`（micromamba env 的 pip-script.py / condabin*.bat / tclConfig.sh 等 8 个）：
  shebang/hook 中的旧路径。若 recon 环境再次使用，建议重建 env 而非手改。

### 4.5 环境变量 / 配置检查

- `JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot`（正常，与项目无关）
- 系统 PATH、用户环境变量中**无** `C:\FL26_Mod` 残留。
- 无脚本参数化配置文件依赖旧绝对路径（Previewer 之外）。

## 5. 本次审计修改清单（全部）

1. `tools\FL26_AvatarPreviewer\ProjectSettings\ProjectVersion.txt`：
   `2020.3.9f1c1 (ef65345766d1)` → **`2020.3.49f1 (a8928a80ccc7)`**（恢复被污染的正确版本，见第 6 节）
2. `tools\FL26_AvatarPreviewer\Assets\Scripts\Runtime\PreviewerBootstrap.cs`：路径动态化（见 4.1）
3. `tools\FL26_AvatarPreviewer\PC_AVATAR_PREVIEWER_SETUP.md`：路径更新（见 4.1）
4. `tools\FL26_AvatarPreviewer\README.md`：路径更新 + 陈旧描述修正（见 4.1）
5. `recon\reports\PC_AVATAR_PREVIEWER_STATUS.json`：baseline 键/候选路径更新为 D 盘 + migration 字段（见 4.1）
6. 本文件 `PATH_MIGRATION_AUDIT.md`（新建）

**未修改**：任何 .unity3d / .apk / keystore / 原始资产 / 历史报告正文 / face_benchmark 结果。

## 6. 审计中发现的额外事实（重要）

1. **ProjectVersion.txt 在迁移前（2026-09-03 22:48）已被污染**：
   `tools\FL26_AvatarPreviewer\editor.log / editor2.log / editor3.log`（mtime 9月3日 22:52-23:22，随项目拷贝到 D 盘）
   显示当晚曾用 `D:\Unity\Editor\Unity.exe`（= **2020.3.9f1c1** 中国版）以 `-projectPath C:\FL26_Mod\tools\FL26_AvatarPreviewer`
   启动，Unity 启动早期即把 ProjectVersion.txt 覆写为自身版本 2020.3.9f1c1。三次启动均未完成导入
   （工程内无 Library\），License 未激活（import.log: "Unity has not been activated with a valid License"，
   manuallic.log 生成了 `Unity_v2020.3.9f1c1.alf` 但激活失败 exit 1）。
   本次审计已将其恢复为 2020.3.49f1，待真正的 2020.3.49f1 首次打开时重新生成 ProjectSettings。
2. **本机 Unity 编辑器现状**（2026-09-05）：
   - `D:\Unity\Editor` = Unity **2020.3.9f1c1**（中国版，非目标版本）
   - `D:\2022.3.62t14\Editor` = 团结引擎 Tuanjie 2022.3.62t14（非目标版本）
   - Unity Hub：`C:\Program Files\Unity Hub\Unity Hub.exe`，secondaryInstallPath=`D:\`
   - **2020.3.49f1 未安装** → 按规则 `PC_PREVIEW_VALID` 维持 **BLOCKED**，不下载安装。
3. **许可证**：`C:\ProgramData\Unity\Unity_lic.ulf` 存在（何时生效未考证；若安装 2020.3.49f1 后仍提示无许可，
   用 Hub 重新激活一次即可）。

## 7. 工具链清单（2026-09-05 实测）

| 工具 | 状态 | 位置 |
|---|---|---|
| Java/JDK | ✅ 21.0.12 (Microsoft) | `C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot`（JAVA_HOME 已设） |
| adb | ✅ | `D:\FL26_Mod\android-sdk\platform-tools\adb.exe`（不在 PATH，需全路径调用） |
| apksigner / zipalign | ✅ | `D:\FL26_Mod\android-sdk\build-tools\36.0.0\` |
| Python | ✅ 3.13.14 | 系统 PATH；另有 `face_benchmark\envs\envs\recon` 项目内 env |
| Unity Hub | ✅ | `C:\Program Files\Unity Hub\Unity Hub.exe` |
| Unity Editor 2020.3.49f1 | ❌ 未安装 | 现有：2020.3.9f1c1（D:\Unity\Editor）、Tuanjie 2022.3.62t14（D:\2022.3.62t14） |

## 8. Gate 状态速览

全部 7 个 Gate 维持 **BLOCKED**（与 2026-09-03 记录一致，根因不变：2020.3.49f1 未安装）。
本次审计无新增 RED 项；ProjectVersion.txt 污染属于"工程待打开"状态问题，已修复，不影响静态检查结论。
