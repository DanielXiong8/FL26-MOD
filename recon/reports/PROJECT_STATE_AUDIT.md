# FL26 Custom Player 项目状态审计（PROJECT STATE AUDIT）

**审计日期**: 2026-08-31 23:54 CST
**审计性质**: 只审计，不开发
**最终目标（重新锁定）**: PC 照片 → 人脸建模（高相似度）→ 设置姓名/位置/17属性 → 选球队 → 静态球员写入 APK → 打包签名 → Android → League 模式原生使用

---

## 三、事实状态矩阵（Evidence-based）

| 功能 | 状态 | 证据 |
|------|------|------|
| APK 提取/修改/重打包 | 🟢 GREEN | base_debuggable2.apk→dist APK，zipalign+apksigner 全链路可用 |
| APK 签名 | 🟢 GREEN | fl26_test.keystore + apksigner 成功 |
| APK 安装真机 | 🟢 GREEN | adb device 95e2d9a，安装成功 |
| PlayerCareer 存档编辑器 | 🟢 GREEN | Step 3B 10/10 gates，SQLite+protobuf |
| Players 表解析 | 🔴 RED | parse 在 offset 0x8 失败，头后是国家表未跳过 |
| Players 表写回 | 🟡 YELLOW | modify_bundle.py 存在（改现有球员+10B），未真机验证 |
| 新增静态 PlayerID | 🔴 RED | 从未生成过 |
| MasterLeaguePlayer | 🟡 YELLOW | CSV 已读取（583行），作用=阵容表（部分） |
| ClubPlayer 解析 | 🔴 RED | 二进制 800KB 未解析 |
| PlayerAppearanceTable | 🔴 RED | 二进制 1.5MB 未解析 |
| StarPlayerAppearance | 🟡 YELLOW | 二进制已读出，映射球星名→资源 |
| Face Texture 导出 | 🟢 GREEN | face_african_new1 导出 512×512 PNG |
| Face UV 数值化 | 🔴 RED | 未读 Mesh UV channel，未数值化 |
| 照片→Custom Face Texture | 🔴 RED | 未实现 |
| 照片→Custom 3D Head | 🔴 RED | 未实现 |
| 17属性（User Player） | 🟢 GREEN | Step 3B 验证 |
| 17属性（静态 League） | 🔴 RED | 未验证 |
| Team 注入 | 🔴 RED | 仅分析，未真机验证 |
| APK 一键 Build | 🟡 YELLOW | step3a_build.ps1 存在，未自动化到最终包 |

---

## 四、审计 1：APK / Build Pipeline

| 步骤 | 状态 | 证据路径 |
|------|------|----------|
| Original APK | 🟢 | `build/base_debuggable2.apk` 396,184,511B SHA256 c0e977b54b9b56aa |
| Working copy | 🟢 | base_debuggable2.apk（原始+side-by-side） |
| Extract | 🟢 | zipfile/UnityPy 读取正常 |
| Modify | 🟡 | modify_bundle.py（改现有球员，未新增） |
| Replace | 🟡 | modified/ 输出存在但未回填测试 |
| Rebuild | 🟢 | axml_add_activity.py → base_saveexport.apk |
| Align | 🟢 | zipalign -p -f 4 |
| Sign | 🟢 | apksigner + fl26_test.keystore |
| Verify | 🟢 | 安装成功 |
| Install | 🟢 | adb install -r 成功，设备 95e2d9a |

**结论**: APK 构建流水线**完整可用**。但只用于注入 Activity/Frida gadget，**未用于注入静态球员**。

---

## 五、审计 2：Player 数据（核心）

| 问题 | 答案 | 状态 |
|------|------|------|
| 1. Players parser 正常？ | **否**。parse_plyrcsv0 在 offset 0x8 失败（头8字节`plyrcsv0`后是**国家名表**，未正确跳过） | 🔴 RED |
| 2. UTF-16 surrogate 解决？ | **否**。读 name 时遇 surrogate 崩溃 | 🔴 RED |
| 3. 稳定解析全部记录？ | 否 | 🔴 RED |
| 4. 稳定写回记录？ | 部分。modify_bundle.py 实现了 serialize，但未完整验证 | 🟡 YELLOW |
| 5. 新 PlayerID 生成过？ | **否** | 🔴 RED |
| 6. 新 PlayerID 进 APK？ | 否 | 🔴 RED |
| 7. 新 PlayerID 真机 League 显示？ | 否 | 🔴 RED |

**⚠️ 之前报告中的 180000–299999 区间只是候选假设，标记为 YELLOW/UNVERIFIED。只有真机新增 Player 成功才能标 GREEN。**

---

## 六、审计 3：League / MasterLeaguePlayer

**引用链**：
- MasterLeaguePlayer → PlayerID → Players → Appearance → League Runtime → Match

| 环节 | 验证状态 |
|------|----------|
| MasterLeaguePlayer→PlayerID | 静态推断（CSV 映射，未验证运行时读取） |
| PlayerID→Players | 静态推断（未验证） |
| Players→Appearance | 静态推断（未验证） |
| Appearance→League Runtime | 未知 |
| League Runtime→Match | 未知 |

**Q1: MasterLeaguePlayer 是什么？**
🟡 部分。它是一个 **League 阵容映射表**（CSV: `Teamid,Playerid1|Playerid2`）。583 行，17 队有阵容，565 队空。但**不确定**它是 PRIMARY_LEAGUE_ROSTER、SECONDARY_ROSTER 还是 MODE_INDEX。需运行时验证。

**Q2: 新增静态球员需改哪些表？**
未定。候选：`Players`（必改）、`MasterLeaguePlayer`（若阵容走此表）、`PlayerAppearanceTable`（若需独立外观）、`avatar.unity3d`（若需自定义脸）。**全部待验证，不沿用旧结论。**

---

## 七、审计 4：League 真正的新球员测试

```
EXISTING PLAYER MUTATION:
PASS (Step 3B, PlayerCareer SQLite, 10/10 gates) — 但这是存档修改，非静态表

NEW STATIC PLAYER:
UNTESTED / FAIL — 从未在 League 真机测试过新增静态球员

CURRENT HARD BLOCKER: NEW STATIC PLAYER 未通过
```

---

## 八、审计 5：Appearance

```
custom_appearance_status: RED
```
- 新 Player 独立 Appearance：未实现
- AppearanceId 分配：未知
- 是否存在最大值：未知
- 是否有缓存：未知（ProfilePicAtlasCache 存在但未涉及注入）
- 是否必须同步其他表：未知

---

## 九、审计 6：Avatar / Face（拆 4 阶段）

| 阶段 | 状态 | 证据 |
|------|------|------|
| A. 已有 Face Texture 导出 | 🟢 GREEN | face_african_new1 导出 512×512 PNG |
| B. Face UV 已理解 | 🔴 RED | 未读 Mesh UV channel，未数值化 |
| C. 照片→Custom Face Texture | 🔴 RED | 未实现 |
| D. 照片→Custom 3D Head Mesh | 🔴 RED | 未实现 |

**⚠️ A 不等于 C/D。已导出已有纹理 ≠ 能生成自定义纹理。**

---

## 十、特别审计 UV

face_african_new1 (512×512 RGBA)：
1. 读取对应 Mesh UV channel？**否** 🔴
2. UV 数值化？**否** 🔴
3. Landmark→UV 映射实现？**否** 🔴
4. 输出稳定 Custom Face Texture？**否** 🔴
5. 游戏内成功显示？**否** 🔴

**结论**: "看起来像标准脸 UV" → **不能标 GREEN**。UV 完全未处理。

---

## 十一、审计 7：高相似度人脸建模

| Level | 状态 |
|-------|------|
| Level 1: 照片→2D face texture | 🔴 RED |
| Level 2: 照片→FL26 face texture | 🔴 RED |
| Level 3: 照片→3D head mesh | 🔴 RED |
| Level 4: 3D head→FL26-compatible head | 🔴 RED |
| Level 5: FL26 真机显示有相似度 | 🔴 RED |

**现在处于 Level 0**：仅能导出游戏已有纹理，照片→任何自定义脸均未实现。

---

## 十二、审计 8：17 项属性

| 能力 | User Player (Step 3B) | 静态 League Player |
|------|----------------------|--------------------|
| 从现有 Player 读取 | 🟢 | 🔴 未验证 |
| 创建新的 Player data | 🟢 | 🔴 未实现 |
| 设置任意值 | 🟢 | 🔴 未实现 |
| 写入 APK | 🟢（存档） | 🔴 未实现 |
| League 中显示 | 🟢（PlayerCareer） | 🔴 未验证 |
| 比赛中影响球员 | 🟢 | 🔴 未验证 |

**⚠️ 17 属性只在 User Player（存档编辑器）验证过。静态 League Player 是否支持 17 项自定义属性：完全未验证。**

---

## 十三、审计 9：Team 注入

- Custom Player → 指定 Team → League → Match：**仅分析完成，未真机验证** → 🟡 YELLOW
- 只验证过 ClubPlayer（Step 3B 存档），**没有 League 新球员实机验证**

---

## 十四、审计 10：当前代码与工具

### scripts/（按可复用性）
| 工具 | 状态 |
|------|------|
| axml_add_activity.py | 🟢 READY_TO_REUSE（APK 注入 activity/Frida） |
| axml_debuggable.py | 🟢 READY_TO_REUSE |
| axml_pkg_rename.py / arsc_pkg_rename.py | 🟢 READY_TO_REUSE |
| modify_bundle.py | 🟡 PARTIAL（改现有球员，需修复解析器） |
| step3a_build.ps1 | 🟡 PARTIAL（未自动化最终包） |
| parse_players.py / parse_player_record.py | 🔴 PARTIAL（解析器不完整） |
| find_player_records.py | 🔴 PARTIAL |
| frida_*.py / frida_hook.js | 🟡 OBSOLETE（运行时 hook 已放弃） |
| analyze_gamedata.py / check_tables.py | 🟡 PARTIAL（探索用） |
| clubplayer_regen.py / clubplayer_regroup.py | 🟡 PARTIAL |
| 其余 search_*/inspect_*/query_*.py | 🟡 探索用，部分废弃 |

### tools/
| 工具 | 状态 |
|------|------|
| custom_player_editor/{editor,protobuf_editor,sqlite_store}.py | 🟢 READY_TO_REUSE（PlayerCareer 存档） |
| saveexport/（Java bridge） | 🟢 READY_TO_REUSE（MIUI workaround） |

**⚠️ 没有 build_apk.ps1 一键构建脚本；没有专门 players_parser 完成版。**

---

## 十五、审计 11：当前工作成果

### 真正可复用资产
- `build/base_debuggable2.apk`（原始工作副本）
- `dist/fl26_mod_saveexport.apk`（已签名含 activity + Frida）
- `tools/custom_player_editor/`（存档编辑器）
- `recon/02_engine/il2cpp/out/dump.cs`（21.8MB 反编译）
- `build/avatar.unity3d`（67.6MB，85 张脸纹理）
- `build/gamedata.unity3d`（15MB，Player 表/球队表）

### 中间实验文件（非复用）
- `build/frida_hook.js`、`frida_log*.txt`（运行时 hook 已弃）
- `saves/*.txt` 分析日志
- `modified/`（修改过但未验证的 bundle）
- 1026 个暴力测试 PNG（已证明无效）

### 已废弃
- Frida gadget 注入方案（用户转向构建期注入）
- EditablePlayerIcon 运行时路径（死代码）

---

## 十六、审计 12：当前真正的最终路径

```
PC照片
 ↓
Face Reconstruction          [🔴 RED]
 ↓
Custom Face/Head             [🔴 RED]
 ↓
Player Builder               [🔴 RED]
 ↓
Players 表                   [🔴 RED - 解析器不完整]
 ↓
League Roster                [🟡 YELLOW - MasterLeaguePlayer CSV 已读]
 ↓
Appearance                   [🔴 RED]
 ↓
Avatar                       [🟡 YELLOW - 纹理可导出但 UV 未处理]
 ↓
APK Build                    [🟢 GREEN - 流水线完整]
 ↓
Android                      [🟢 GREEN - 安装验证]
 ↓
League                       [🔴 RED - 未真机验证新球员]
 ↓
Match                        [🔴 RED]
```

---

## 十七、概念区分

| 概念 | 状态 |
|------|------|
| 1. 已验证（真机） | APK 构建/安装、存档编辑器 |
| 2. 已实现未真机验证 | modify_bundle.py（改现有球员）、MasterLeaguePlayer 读取 |
| 3. 理论上可行 | 静态球员注入、人脸建模（只有架构分析） |

---

## 十八、15 个核心问题

1. **新增静态 PlayerID？** 🔴 否。解析器不完整。
2. **新 PlayerID 真机 League 出现？** 🔴 否。
3. **League roster 由谁控制？** ❓ 未知（MasterLeaguePlayer 是 CSV 阵容表，部分）。
4. **MasterLeaguePlayer 是什么？** 🟡 部分，League 阵容映射表（17/582 队有阵容），具体作用未验证。
5. **新球员改哪几张表？** ❓ 未定。候选 Players + MasterLeaguePlayer + PlayerAppearanceTable + avatar，全部待验证。
6. **Appearance 独立创建？** 🔴 否。
7. **Avatar 独立创建？** 🔴 否。
8. **Custom Face Texture 成功？** 🔴 否（仅能导出已有纹理）。
9. **3D Head 成功？** 🔴 否。
10. **照片→游戏脸？** **Level 0**（仅导出，无生成）。
11. **17属性用于新静态球员？** 🔴 未验证（只在 User Player 存档验证过）。
12. **指定球队真机验证？** 🔴 否。
13. **APK 一键 Build 最终测试包？** 🟡 部分。流水线可用但未自动化，未含球员注入。
14. **当前唯一/主要阻塞？** **Players 表解析不完整 + 静态球员注入未真机验证**（需先打通"新增静态球员→League 显示"最小闭环）。
15. **距离最终目标 Gate？** 见下方最终状态图。

---

## 十九、最终状态图

```
══════════════════════════════════
FL26 CUSTOM PLAYER FINAL PIPELINE
══════════════════════════════════

PHOTO
  ↓
FACE RECONSTRUCTION       [R]
  ↓
FL26 FACE/HEAD            [R]
  ↓
PLAYER DATA               [R]
  ↓
17 ATTRIBUTES             [R - 静态未验证]
  ↓
TEAM ASSIGNMENT           [R]
  ↓
LEAGUE ROSTER             [Y]
  ↓
APPEARANCE                [R]
  ↓
AVATAR                    [Y - 纹理可导出, UV未处理]
  ↓
APK BUILD                 [G]
  ↓
ANDROID INSTALL           [G]
  ↓
LEAGUE                    [R]
  ↓
MATCH                     [R]
  ↓
FINAL GOAL                [R]
══════════════════════════════════
```

---

## 二十、审计执行规则

本次只审计，未开发。未为了让任何 Gate 变绿而主动开发。

**纠正之前报告**：
- 之前"180000-299999 球员 ID 区间"标记为 **YELLOW/UNVERIFIED**（从未真机验证新增球员）
- 之前 Step 3B 的"17属性"成功**只限于 User Player 存档**，不能类推到静态 League Player

---

## 总结

```
=== FL26 PROJECT STATE AUDIT ===

Overall:       RED（距最终目标大部分未实现，仅构建/存档链路完成）
Current phase: Step 3D 前期（构建期注入架构分析，尚未落地）
Completed:     APK 构建流水线、PlayerCareer 存档编辑器、Face 纹理导出、MasterLeaguePlayer CSV 读取
Partially completed: Players 表修改（改现有）、avatar 纹理导出、League 阵容表读取
Blocked:       新增静态球员（解析器不完整）、人脸建模（UV 未处理）、League 真机验证

Hard blocker:  Players 表解析不完整（plyrcsv0 头后国家表未正确跳过）+ 静态球员注入未真机验证
Next recommended single action: 修复 plyrcsv0 解析器（正确跳过国家名表），打通"新增一个静态球员→League 显示"最小闭环
```
