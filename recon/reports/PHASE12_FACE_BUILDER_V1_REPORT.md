# PHASE12_FACE_BUILDER_V1_REPORT.md — FL26 Face Builder v1 Productization

> 日期：2026-09-06。Phase 12 = 将已验证的核心技术整合成**单入口、可重复、可恢复**的桌面工具。
> 基线保护：`recon\baselines\FULL_PIPELINE_VALID_GREEN\`（PHASE12_BASELINE_LOCKED = true，7 文件 SHA256 清单）。

## A. Dashboard 是否已经成为唯一入口

**是。** `tools\FL26_FaceDashboard\dashboard.py` 现在覆盖完整流程：
照片载入 → Candidate Pool（调用既有 generate_candidates.py）→ 候选看板（REJECT 灰置）→ 2D/3D 预览 → 外观调节（b1/b4/b7/b10/b14）→ ACCEPT FACE → **Player Information（姓名/位置/球队/17 项）** → **BUILD APK**（编排既有 phase11 注入脚本，不复制实现）→ **INSTALL TO DEVICE**。
注入逻辑仍在已验证的 `phase11_e2e_inject.py` / `phase11_e2e_avatar_inject.py` 中，Dashboard 仅编排（PHASE11_CONFIG 环境变量传参，零逻辑复制）。

## B. 是否可以从照片一路 BUILD APK

**是。** Dashboard 内部顺序 = final_face 校验 → PID 分配（三表查重）→ build_config.json → phase11_e2e_inject.py（PHASE11_CONFIG 覆盖 pid/名/队/属性）→ 产物 APK。
照片到 BUILD 的编排路径已在无 GUI 模式下实测（regression_ma_jiantao/build_config.json → config override loaded ✓ → sign/verify OK ✓）。

## C. 是否支持姓名/位置/17能力/球队

**支持。** Player Information 面板：
- Name（文本框，默认 "Ma Jiantao"）
- Position（下拉：3=FW 前锋——目前唯一已确认位置码，其余待逆向，界面不伪造）
- Team（下拉：Manchester City 20026 / China national team 10059 / London Red 20030——三个已验证球队）
- Jersey Number：**NOT YET EXPOSED**（不伪造）
- 17 Attributes：逐项输入框（1-99 校验），字段名与 Players 表解析一致

## D. 是否支持安装到 Android

**支持。** INSTALL TO DEVICE 按钮：adb install -r（BUILD+SIGN+VERIFY=GREEN 才允许）；成功显示 "PASS — 进 League 验证球员"，失败显示具体错误。不自动破坏当前安装。

## E. 是否破坏 STEP11 GREEN baseline

**未破坏。**
- 基线已冻结：`recon\baselines\FULL_PIPELINE_VALID_GREEN\`（STEP11 报告/状态/注入脚本/成功 APK/final_face/SHA256 清单，PHASE12_BASELINE_LOCKED=true）
- STEP11_FINAL_E2E_REPORT.md / STATUS.json 保留未覆盖
- phase11 注入脚本：仅加配置读取（默认值 = 已验证值，无配置时行为与 Step 11 完全一致）
- DashboardRender.cs / Step9BatchRunner.cs / PreviewerBootstrap.cs 零改动

## F. Ma Jiantao regression 是否 PASS

**构建路径回归 PASS**（无 GUI 实测）：regression_ma_jiantao/build_config.json → PHASE11_CONFIG → config override loaded ✓ → 注入完成 → sign/verify OK ✓。
**完整 MATCH_E2E 回归**：待设备重连后由用户打一场确认（上一次同配置真机结果 = "在，像！"，本轮回归使用完全相同的注入参数，预期一致）。

## G. 当前 FACE_BUILDER_V1 状态

**YELLOW → 待一场真机比赛后转 GREEN**。工具完整可用，剩余唯一未验证项 = 通过 Dashboard 流程产出的 APK 在真机打满一场比赛的最终回归（设备重连即做）。

## Gate

| Gate | 状态 |
|---|---|
| PHASE12_BASELINE_LOCKED | 🟢 |
| STEP12_SINGLE_ENTRY | 🟢 |
| STEP12_PLAYER_INFO | 🟢 |
| STEP12_TEAM_SELECTOR | 🟢 |
| STEP12_BUILD_ORCHESTRATION | 🟢 |
| STEP12_INSTALL_GATE | 🟢 |
| STEP12_PID_ALLOCATION | 🟢 |
| FACE_BUILDER_V1 | 🟡（待真机回归一场） |

## 已知限制（诚实记录）

1. 外观调节的 b4/b7/b10/b14 无 PC 实时预览效果（真机生效；FaceMaterialSupplier 运行时逻辑未逆向）
2. 3D 预览为 batch 渲染（约 1-2 分钟/次），连续旋转缩放需 Unity Play 模式
3. 位置码仅 3=FW 已确认；其余未逆向（界面不伪造）
4. Jersey Number 未开放
5. 设备 USB 间歇断连（已知硬件问题）导致安装轮询等待


# 11. 最终验收（2026-09-06 用户真机确认）

用户完成完整比赛后确认："可以全部正常"。
**FACE_BUILDER_V1 = GREEN**。完整链路：照片 → MICA → 适配 → bake8 → 候选池 → Dashboard 选脸调参 → ACCEPT FACE → 球员注入（曼城 20026，完整克隆 Yang J. 外观 + f1=1）→ APK 签名安装 → League 首发上场 → 完整比赛无崩溃。

**回归配置**：pid 175923 / nat=13（中国代码，由队友扫描确认）/ fa=11939 fb=305 fc=16054（Onahi 头模代码）/ PA b1=22 b14=31 / 曼城 20026 / f1=1。
