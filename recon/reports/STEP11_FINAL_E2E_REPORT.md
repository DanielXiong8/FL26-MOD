# STEP11_FINAL_E2E_REPORT.md — FL26 End-to-End Final Acceptance

> 日期：2026-09-05。本阶段不是继续开发，而是把已有成果收敛成**可被证明的完整闭环**。

## A. 17 项属性是否已有真实验证证据

**有。** 决定性证据（此前被记忆断档掩盖）：

- `D:\FL26_Mod\screenshots\fl26_squad_scroll.png`（9/1 00:58）：London Red 阵容界面中弹出 **"CustomeaguTest"** 球员卡（总评 94、Age=1980），六维 **SPD 79 / SHO 90 / PAS 97 / DRI 92 / DEF 95 / PHY 88**。
- `D:\FL26_Mod\screenshots\fl26_v5.png`（9/1 00:59）：同一测试球员在 SUB（替补）面板，六维 **SPD 94 / SHO 84 / PAS 88 / DRI 88 / PHY 88**。
- 两张截图来自**不同注入配置轮次**，六维值随之不同——证明游戏读取并计算了注入的 17 字节（81-97 测试模式），而非显示默认值。

## B. 状态冲突裁决

| 记录 | 裁决 |
|---|---|
| STEP_4A 报告 RED（STATIC ATTRIBUTES / MATCH 未验证） | 对 **180001 轮次成立**（Round 2/3：Squad 18/32 未见新球员，ROSTER_GATE 过滤）——该报告自身的"差分定位"建议随后被执行 |
| 接管简报"已跑通" | **属实**——v3/v5 迭代（顺序 ID / ClubPlayer 插入修正）有真机截图 |
| 9/3 记忆"17 属性未真机验证" | **记忆断档误标**：9/1 凌晨 00:00-12:00 的 4A 迭代在 OpenClaw 记忆中无记录（9/1 记忆文件从 12:15 开始） |

`STEP11_STATE_RECONCILED = GREEN`（详见 `STEP11_EVIDENCE_MATRIX.md`：12 GREEN / 2 YELLOW）。

## C. 是否需要补做最小真机测试

**需要但范围缩小**：14 项中仅 2 项 YELLOW（位置显示未捕获、**新球员实际上场比赛**无直接证据），且最后一次迭代（v9，顺序 ID 175923）无真机截图。因此今天直接构建了包含 E2E 球员的最终 APK（见 D/E），待设备在线安装后补齐。

## D. 照片 → final_face（✅ 完整）

```
face_benchmark/inputs/test01_front.jpg（马健涛正面照）
→ generate_candidates.py（8 候选，tilt/seam/coverage 自动检测，c1/c2 REJECT）
→ c4 最优（final_score=0.734, photo_fidelity=0.704）
→ Dashboard 看板 + 人工调参（Step 10，b1/b4/b7/b10/b14）
→ ACCEPT FACE
→ face_benchmark/runs/test01/final_face/{baked.png, face_manifest.json}
```

`face_manifest.json`（schema `fl26_final_face_v1`）含 source_photos、selected_candidate=c4、appearance_patch={b1:22,b4:0,b7:127,b10:0,b14:42}、provenance。

## E. final_face → APK（✅ 完整）

`scripts/phase11_e2e_inject.py`（新增）：
- 基座 = `dist/fl26_allchina_v5.apk`（设备当前安装的马健涛 mod）
- 注入 = Players 52640→52641（**pid 175923 "Ma Jiantao"**，nat=43 中国，b1=22，attrs 81-97）+ ClubPlayer London Red +1 + PlayerAppearanceTable 52646→52647（克隆 Ralla 并 patch b1=22/b4=0/b7=127/b10=0/b14=42——**把 final_face 的 appearance_patch 写进 PA 记录**）
- 输出 = `dist/fl26_e2e.apk`，zipalign + apksigner sign **OK** + verify **OK**

## F/G. Android League 与完整比赛

**BLOCKED**：adb 设备在 E2E APK 构建完成后掉线（`adb devices` 空），安装无法执行。设备重连后：
1. `adb install -r D:\FL26_Mod\dist\fl26_e2e.apk`
2. League → London Red → 确认 "Ma Jiantao"（94 总评、六维 84-97 区间、马健涛脸模 b1=22→face_eastAsia_new1）
3. 替补登场打满一场 → `MATCH_E2E` 裁决

## H. Gate 与 FULL_PIPELINE_VALID

| Gate | 状态 |
|---|---|
| STEP11_STATE_RECONCILED | 🟢 |
| STEP11_PLAYER_READY | 🟢 |
| STEP11_APK_READY | 🟢 |
| STEP11_ANDROID_READY | ⏸ BLOCKED（设备掉线） |
| STEP11_LEAGUE_READY | ⏸ BLOCKED |
| STEP11_MATCH_E2E_READY | ⏸ BLOCKED |
| **FULL_PIPELINE_VALID** | ⏸ **BLOCKED**（7/10 项 GREEN，3 项等设备） |

完整管线清单：照片✓ 候选✓ 故障检测✓ 人工调参✓ final_face✓ 玩家注入✓ APK构建签名✓ | Android安装⏸ League出现⏸ 完整比赛⏸

## I. 距离 FL26 Face Builder v1 还剩什么

1. **设备重连后的真机验收**（半天）：安装 fl26_e2e.apk → League 阵容/替补登场/完整比赛 → MATCH_E2E 裁决 → FULL_PIPELINE_VALID。
2. **Dashboard 与真机验证的衔接**（可选，1 天）：把 ② 的验收结果回写 Dashboard（验证状态徽章）。
3. **Face pipeline 质量提升**（可选，已冻结）：c4/ea3 烘焙的眼区修复（当前渲染的绿眼睛+闭眼贴图痕迹的来源）——用户已裁决冻结，仅在最终质量不满意时重启。

**除真机验收外，链路上没有其它未完成项。**

## 7. 设备重连自动续跑

设备重连（adb devices 出现 95e2d9a）后执行：

```
D:\FL26_Mod\android-sdk\platform-tools\adb.exe install -r D:\FL26_Mod\dist\fl26_e2e.apk
```

安装成功 → 用户导航 League → London Red → 验证 "Ma Jiantao"（94 总评、六维 84-97、
马健涛脸模）→ 替补登场 → 完整一场比赛 → MATCH_E2E 裁决 → FULL_PIPELINE_VALID。

## 8. MATCH_E2E = PASS —— 完整链路闭环（2026-09-06 用户裁决）

用户真机完成完整比赛后确认："全部正常"（Ma Jianto 首发上场、无崩溃、表现正常）。

**FULL_PIPELINE_VALID = GREEN**。完整链路逐段验证完毕：

| 段 | 验证方式 |
|---|---|
| 照片输入 | 3 张新照片（OneDrive\Desktop\马健涛\1/2/3.jpg） |
| MICA 重建 | outputs/mica/mjt1-3/（GPU，mesh/identity/kpts） |
| 适配器四阶段 | stage1 residual 0.0106 → 2 → 2b TPS → 2c → fl26_ea1_adapted.obj |
| bake8 重新烘焙 | baked_mjt_v1.png（新照片五官完整） |
| 双注入 | MICA verts → face_EastAsia_new1 网格；fresh bake → face_eastAsia_new1 贴图 |
| 球员注入 | pid 175923 "Ma Jiantao" 完整克隆队友（Yang J./Onahi 模板）+ f1=1 + PA |
| APK | fl26_e2e.apk 签名验证 OK |
| 安装 | adb install Success（多次） |
| 阵容 | Man City 阵容出现 "Ma Jiantao"（94 总评）——用户真机确认 |
| 完整比赛 | 用户真机确认"全部正常"（上场、无崩溃、表现正常） |

## 9. 状态冲突最终裁决（存档）

- 旧记录"新静态球员已跑通" = **属实**（4A arsenal_v3 轮真机截图：CustomeaguTest 出现在 London Red 阵容+属性显示）
- STEP_4A 报告的 RED = **对 180001+无 f1=1 轮次成立**（ROSTER_GATE 过滤；arsenal_v3 的 f1=1 修复后通过）
- 9/3 记忆"17 属性未验证" = **记忆断档误标**（9/1 凌晨 4A v3-v9 迭代无记忆记录）
- 关键修复三件套：f1=1（首发优先）+ fa/fb/fc=0（不引用不存在的头模）+ 外观完整克隆真实队友（fa/fb/fc+PA 原样）

## 10. 中国队对照实验结论（A/B）

- 真实中国队 = **team 10059**（25 人：Yang J./Le L./Zhan L.P./Wu L./Liu D./Wei/Gao/Wan S./Ling L./Da W./Xe P. 等，全 nat=24）
- E2E 球员（Yang J. 完整克隆）加入 10059 → **出现 + 脸与队友一致（马健涛）** ✓
- 对照结论：**注入逻辑完全复用 OpenClaw 成功逻辑**；Man City 与 CHN 的差异 = 队伍上下文（头模分配跟随外观克隆的正确性），克隆真实队友时任何队伍都可渲染
