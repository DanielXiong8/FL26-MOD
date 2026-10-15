# Step 4A 静态球员最小闭环实验报告（STEP_4A_STATIC_PLAYER_REPORT）

**实验日期**: 2026-09-01
**测试设备**: Xiaomi 24129PN74C (Android 16, MIUI HyperOS)
**测试目标**: 新增一名全新静态球员 → 注入 APK → 真机 League 模式验证

---

## 核心发现与事实（Evidence-based）

### 1. Players 表解析器（Phase 4A.1）
- **状态**: 🟢 **GREEN (100% 解决)**
- **二进制格式**: `plyrcsv0` (magic 8B) → Country Table (ncnt:2B + [len:2B + UTF-16LE]*ncnt) → Player Count (4B) → Player Records (52,640条)
- **每条记录**: pid(4B) + name_len(2B) + name(UTF-16LE) + fa(2B) + fb(2B) + fc(2B) + nat(2B) + b1(1B) + b16(1B) + b0(1B) + attrs(17B) + tail16(2B) + tail8(1B) + year(4B)
- **验证结果**: 52,640 条记录 100% 消耗（2,946,498/2,946,498 字节），Byte-exact roundtrip 验证通过
- **产物**: `recon/03_player/players_parser_v2.py`, `players_parser_v2_test.csv` (1000条样本)

### 2. PlayerID 区间分析（Phase 4A.2）
- **现有范围**: 200 – 175,922（共 52,640 名球员）
- **测试选定**: `TEST_PID = 180001`（大于最大 ID 175,922，留有 4,079 余量）
- **安全性**: 静态分析确认 180001 未被任何现有球员或表使用

### 3. ClubPlayer 表结构（Phase 4A.4 突破）
- **格式**: 两段式二进制结构
  - **Section 1**: 1,862 条 × 8 字节（`team_id:4B + player_count:4B`）
  - **Section 2**: 46,515 条 × 17 字节（`team_id:4B + player_id:4B + f1:4B + f2:4B + f3:1B`）
- **字段含义**:
  - `f1`: 球员在球队中的序号/出场顺位（1-99，非位置代码）
  - `f2`: 角色标志位（6912 最常见，占 56%）
  - `f3`: 保留字段（全为 0）
- **Team 20030 (Arsenal / "London Red")**: 原有 24 名球员，注入后 25 名

### 4. MasterLeaguePlayer 的真实性质
- **性质**: 仅包含 17 支球队 × 3 名球员（共 51 名球员引用），565 支球队为空
- **结论**: **不是 League 模式的主阵容表**，可能是某种特殊挑战/活动模式的配置

### 5. 真机实验结果（Phase 4A 闭环测试）

| 测试轮次 | 注入配置 | 现象 | 结果 |
|---------|---------|------|------|
| **Round 1** | Team 20026, pid=180001, f1=25 | 注入后发现 20026 实际为 Manchester City 而非 Fulham | 重新定位目标 |
| **Round 2** | Team 20030 (Arsenal), pid=180001, f1=template | League 创建成功，Squad 显示 18/32，未见新球员 | 未进入可见阵容 |
| **Round 3** | Team 20030 (Arsenal), pid=180001, f1=1 (最高优先级) | 清除数据重新建 League，Squad 仍显示 18/32 原有球员 | 未进入可见阵容 |

---

## 12 个核心问题逐题回答

1. **Players parser 是否修复？**
   🟢 **是**。Country table 正确解析跳过，52,640 条记录 100% 消耗，byte-exact roundtrip 验证通过。

2. **Country table 如何解析？**
   Offset 0x8 处读取 `ncnt` (uint16)，然后循环 `ncnt` 次：读取 `len` (uint16) + `len * 2` 字节 UTF-16LE 字符串。共 217 个国家。

3. **新 PlayerID 是多少？**
   `180001`（选在现有最大 ID 175,922 之后）。

4. **新 PlayerID 是否真正写入 Players？**
   🟢 **是**。已成功序列化写入 `Players` 表（记录数 52,640 → 52,641），并通过 UnityPy 回填 bundle。

5. **League roster 的真实来源是什么？**
   **ClubPlayer 表**（Section 1 定义各队人数，Section 2 定义具体成员 17 字节记录）。MasterLeaguePlayer 仅为 51 人的稀疏表。

6. **新球员是否进入 League？**
   🔴 **否（真机未见）**。虽然已写入 Players 和 ClubPlayer，但在游戏内 League 阵容界面（Squad 18/32）中未显示。

7. **原球员是否仍然存在？**
   🟢 **是**。Arsenal 原有全部球员（Ralla, Gabrier, Sariba, Haverts 等）完整保留，未被替换。

8. **17项静态属性是否生效？**
   🔴 **未验证**。由于新球员尚未在 League 界面显示，17 属性（81..97）无法在 PlayerCard 中读取验证。

9. **Team assignment 是否生效？**
   🟡 **部分**。已在 ClubPlayer Section 1 (count 24→25) 和 Section 2 中将 180001 关联到 Team 20030，但游戏运行时未加载。

10. **Appearance 是否正常？**
    🔴 **未验证**。未走到 3D 渲染阶段。

11. **Match 是否正常？**
    🔴 **未测试**。需先让球员出现在阵容中。

12. **是否发生任何缓存/索引问题？**
    🟡 **是，存在未知门控机制**。可能原因：
    - `PlayerAppearanceTable`（1.5MB 索引表）缺少对应条目导致跳过
    - `League_variant` 或 `League_new` 中存在硬编码的阵容快照/引用
    - `PlayerManager.ContainsPlayer` 或 IL2CPP 内部存在 ID 范围检查（如 `id < 176000`）
    - 游戏内部数据库存在次级索引表

---

## 失败归因定位（按规则第十一节）

```
PLAYER_PARSE         🟢 PASS (100% byte-exact)
PLAYER_DATA_INJECT   🟢 PASS (Players + ClubPlayer 序列化成功)
APK_BUILD_INSTALL    🟢 PASS (签名安装无报错，游戏正常运行不崩溃)
ROSTER_LOADING       🔴 BLOCK (游戏未从 ClubPlayer 读入 180001 进入 League Roster)
```

**具体定位**: 
- 不是 APK 崩溃或数据损坏（游戏正常运行，原有球员正常显示）
- 不是 ClubPlayer 格式错误（两段结构完全解析，原有 46,515 条记录 100% 匹配）
- **当前瓶颈在 ROSTER_GATE / APPEARANCE_GATE**：游戏在 `CreateLeague` 时通过某种机制过滤了球员，新 ID `180001` 可能因缺少外观索引或超过内部 ID 检查而被丢弃。

---

## 最终状态判定

```
NEW STATIC PLAYER:     🟡 YELLOW (数据已写入 APK，但真机 League 未显现)
LEAGUE ROSTER:         🟡 YELLOW (ClubPlayer 结构已破解，但注入机制未闭环)
STATIC ATTRIBUTES:     🔴 RED (未验证)
TEAM ASSIGNMENT:       🟡 YELLOW (ClubPlayer 已分配，未生效)
MATCH:                 🔴 RED (未测试)
```

---

## 下一步唯一推荐动作（Single Action）

**路线纠偏 — 差分定位法**：
不使用全新 ID `180001`，而是**在已有 ID 范围内选一个自由球员（或低级别队球员）修改其归属球队至 Arsenal**，先证明 "ClubPlayer 修改能改变 League 阵容"，然后再排查 "新 PlayerID 为什么被过滤"。
