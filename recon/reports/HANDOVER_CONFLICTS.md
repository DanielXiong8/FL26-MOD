# HANDOVER_CONFLICTS.md — OpenClaw memory vs 当前项目文件 冲突检查

> 生成：2026-09-05。检查原则：**不自动覆盖任何一边，记录冲突，以当前实际文件 + 最新验证结果为准。**

## 结论：无阻断性冲突。发现 1 处记忆断档、3 处表述演进、1 处待裁决状态差异。逐项如下。

### 1. 记忆断档（最重要）
- **现象**：OpenClaw 记忆止于 2026-09-03 16:40（Candidate Pool v1 交付）。项目文件显示 9/3 22:19-23:23
  进行了 Step 9 PC Avatar Previewer 的设计/静态检查/状态报告编写，以及当晚的 Unity 2020.3.9f1c1 batchmode 尝试。
  该时段无任何 OpenClaw 记忆条目。
- **裁决**：此段以项目文件为唯一事实来源（PC_AVATAR_PREVIEWER_*.json/md、editor*.log）。
  不属于冲突，属于 gap，Zcode 已在 OPENCLAW_FL26_HANDOVER.md D 节登记。

### 2. "Step 9" 定义演进（非冲突）
- OpenClaw 9/1-9/2 记忆中 "Step 9" = Face Reconstruction Benchmark（MICA vs FaceVerse 收尾）。
- 项目文件（9/3 晚起）中 "Step 9" = FL26 PC Avatar Previewer。
- **裁决**：同一编号被复用于先后两个任务；benchmark 已收尾（benchmark_report.md 在 face_benchmark\adapter\），
  当前 Step 9 指 PC Previewer。以项目文件为准。

### 3. c4 状态表述差异（非冲突）
- OpenClaw 9/3 记忆：c4 首轮最优，"待用户目视 contact sheet 裁决 GREEN"。
- 项目文件（CANDIDATE_POOL_V1_REPORT.md、STATUS.json）：c4 直接作为当前候选/有效过渡预览使用。
- **裁决**：无对立结论；项目文件的后续使用行为视为用户验收的事实结果。c4 = 当前候选维持不变。

### 4. 17 属性静态球员能力表述（记忆已自我修正）
- 8/31 审计记忆：新 PlayerID / 静态球员 17 属性 = RED。
- 9/3 记忆自我修正：modify_bundle.py 已部分实现（Reno id=100373 修改成功）。
- 项目文件 STEP_4A_STATIC_PLAYER_REPORT.md：Step 4A 静态注入已打通。
- **裁决**：记忆内部已随时间自我修正且与项目文件一致（"可注入"为真；"未真机验证静态球员 17 属性"为真且仍未验证）。两者并行记录，不矛盾。

### 5. 路径体系（按任务定义分离，非冲突）
- OpenClaw 记忆全部使用 `C:\FL26_Mod`（LEGACY_ROOT）。
- 当前项目实际位于 `D:\FL26_Mod`（CURRENT_ROOT），SHA256 4/4 验证一致。
- **裁决**：LEGACY / CURRENT 分离记录（见两份 HANDOVER 文件头部），记忆中的 C: 路径永不作为当前路径使用。

## 冲突处理规则（本次起生效）

1. OpenClaw memory 与项目文件不一致 → 记录于本文件，以项目文件 + 最新验证为准，OpenClaw 侧不做任何修改。
2. 新验证结果与 OpenClaw 记忆矛盾时：更新项目报告 + 在本文件追加条目，不回改 OpenClaw 记忆。
3. OpenClaw workspace 保持只读，随时可切回。
