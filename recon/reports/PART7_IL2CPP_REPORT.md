# PART 7 IL2CPP RECOVERY REPORT

**Date**: 2026-08-31 15:45 +08:00
**Environment**: Unity 2020.3.49f1 / IL2CPP v27.1 / arm64-v8a / global-metadata.dat v27 (8.5MB)
**Tool**: Il2CppDumper v6.7.46 (stable, GitHub release `v6.7.46`, SHA256 `F5FC60DFC5C034C1FF3FC651514416EBD47658A63493207734537FD25FA2DEA2`)
**Status**: Read-only structure recovery COMPLETE. No native binary modification.

---

## 1. Player

- **Class**: `public class Player` (TypeDefIndex 9614)
- **Player ID**: `private int <id>k__BackingField` (0x10) — int32
- **Name**: `public string RealName { get; }` / 序列化时 UTF-16LE 写入
- **Position**: `private FormationTool.UIPosition[] <position>k__BackingField` (0x50) — `FormationTool.UIPosition` enum (0=GK..14=CF, 15=SUB)
- **Attributes**: 17 项 short 字段（0x20..0x40，存为 u8）
- **Team reference**: 不在 Player 基类中；在子类 `ClubPlayer.Team` / `ClubPlayer.TeamId` (0x90)
- **其他关键字段**: `age`(0x14), `birthday`(0x18), `height`(0x1C), `weight`(0x1E), `nationality`(0x48, string), `YOB`(0x5C), `preferredFoot`(0x60), `weakfootability`(0x61), `targetRating`(0x62)

## 2. Attributes (17 字节逐一定名)

| 索引 | 属性名 (IL2CPP) | 语义 (中文) | 偏移 | 类型 | 置信度 |
|---|---|---|---|---|---|
| attr_00 | **balance** | 平衡 | 0x20 | short (u8 in bin) | A |
| attr_01 | **reaction** | 反应 | 0x22 | short | A |
| attr_02 | **acceleration** | 加速 | 0x24 | short | A |
| attr_03 | **velocity** | 速度 | 0x26 | short | A |
| attr_04 | **stamina** | 体能 | 0x28 | short | A |
| attr_05 | **agility** | 灵活 | 0x2A | short | A |
| attr_06 | **shotpower** | 射门力量 | 0x2C | short | A |
| attr_07 | **standingtackle** | 站抢 | 0x2E | short | A |
| attr_08 | **slidingtackle** | 铲抢 | 0x30 | short | A |
| attr_09 | **ballcontrol** | 控球 | 0x32 | short | A |
| attr_10 | **dribble** | 盘带 | 0x34 | short | A |
| attr_11 | **shortpass** | 短传 | 0x36 | short | A |
| attr_12 | **highpass** | 长传 | 0x38 | short | A |
| attr_13 | **shot** | 射门 | 0x3A | short | A |
| attr_14 | **volley** | 凌空 | 0x3C | short | A |
| attr_15 | **mental_defensivepositioning** | 防守站位 | 0x3E | short | A |
| attr_16 | **mental_vision** | 视野 | 0x40 | short | A |

**卡片六维**（SPD/POS/DIV/VIS/KIC/REF）由 `PlayerIngameRatingRules` / `UserPlayerRatingRules` 加权公式计算，`UIHexRadarChart` 渲染。

## 3. ClubPlayer (17B 定长记录)

- **Class**: `public class ClubPlayer : Player` (TypeDefIndex 7360)
- `team_id`: `+0` u32 LE → `public int TeamId { get; }` / `TeamsData Team`
- `player_id`: `+4` u32 LE → 100% 闭环指向 Players
- `jersey`: `+8` u8 → `public int CoatNum { get; set; }`
- `role`: `+13` u8 → `public FormationTool.UIRole roleInTeam { get; set; }`
  - **UIRole 枚举**: 0=GK, 1=LB, 2=LCB, 3=CB, 4=RCB, 5=RB, 6=LWB, 7=LDM, 8=CDM, 9=RDM, 10=RWB, 11=LM, 12=LCM, 13=CM, 14=RCM, 15=RM, 16=LAM, 17=CAM, 18=RAM, 19=LW, 20=LF, 21=CF, 22=RF, 23=RW, 24=LS, 25=ST, 26=RS, **27=SUB (替补)**

## 4. Appearance

- **Class**: `public class PlayerAppearanceTable` (TypeDefIndex 9355) + 嵌套 `Player.PlayerApperance` (TypeDefIndex 9611)
- **Lookup**: `public static PlayerAppearanceTable Get(int key)` → 内部用 `public static Dictionary<int, int> dataByid`（player_id → offset）
- **21B 记录字段**:
  - `id` (int, 0x10) — player_id
  - `skinID` (sbyte, 0x14) → `get_skin()` → GlobalTables.skin
  - `faceTextureID` (short, 0x16) → `get_faceTexture()` → GlobalTables.face
  - `hairMeshNameID` (short, 0x18) + `hairColorIdx` (sbyte, 0x1A) → `get_hairMeshName()`
  - `BeardID` (short, 0x1C) + `BeardColor` (sbyte, 0x2A) → `get_Beard()`
  - `eyeID` (sbyte, 0x1E) → `get_eye()`
  - `eyebrowID` (sbyte, 0x1F) → `get_eyebrow()`
  - `headMeshID` (short, 0x28) + `headData` (sbyte[], 0x20) → `get_headMesh()`
- **专属球星**: `StarPlayerAppearance` 表直接声明 (player_id, head, hair, hairTex, face, displayName)

## 5. Save / Load (重大发现：Protobuf 存储)

- **主存档**: `public sealed class ClubPlayerDatabase : IMessage<ClubPlayerDatabase>` (TypeDefIndex 9043) — **Google Protobuf** 格式
  - `MapField<int, ClubPlayerData> Database` (field 1)
  - `MapField<int, FakePlayer> FakePlayerProtos` (field 2)
  - `MapField<int, TeamTactics> UserTeamTactics` (field 5)
  - `MapField<int, PlayerContract> PlayerContract` (field 6)
  - `PlayerTemporaryBoostRecord BoostRecord` (field 7)
- **存档代理**: `LocalArchives` / `ExternalDataAgent` / `ExternalDataArchives`
- **自定义头像存储**: `EditablePlayerIcon`
  - `Save(byte[] datas, Texture2D myTexture)`
  - `IsCustom()`
  - `MakeImage(Action<Texture, Rect> action)`
  - `Dictionary<string, Dictionary<ArchivesDetailType, Dictionary<int, WeakReference<Texture2D>>>> Cache`

## 6. Player Career & UI Flow

- **创建入口**: `Win_StartCareer : WindowBase` (TypeDefIndex 8093)
  - `Fill(UserPlayerSetupData userPlayerSetupData, SelectRoleSceneManager selectRoleSceneManager, TeamsData team)`
  - `Next()`
- **自创球员协议**: `UserPlayerSetupData` (TypeDefIndex 7398)
  - `PlayerName`, `KitName`, `KitNumber`, `Nationality`(eNation), `Position`(UIPosition), `PlayerType`, `targetTeamId`, **`AppearanceId`**
- **生涯主界面**: `Win_PlayerCareer : WindowBase` (TypeDefIndex 8070)
  - `PlayerModelLoader playerModelLoader` (3D 球员模型)
  - `UIHexRadarChart playerRatingChart` (六维雷达图)
  - `GUIUserPlayerBaseInfo userPlayerBaseInfo`
  - `Button btnUpgrade`, `Button btnStats`, `Button btnCalendar`, `Button btnFixtures` ...
- **UI 注入点**:
  - `Win_PlayerCareer` 界面通过 prefab 添加 `[Import Player]` 按钮
  - 或在 `Win_StartCareer` 开局时注入自创数据 `UserPlayerSetupData`
  - 自定义头像直接调用 `EditablePlayerIcon.Save(bytes, texture)`

## 7. Dynamic Player Loading & ID Safety

- **查找机制**:
  - `PlayerManager.allProto` (`List<Player>`) — 静态全量库
  - `PlayerManager.getTemplateById(int id)` → 二分查找 `PlayerIdComparer`（因此 Players 需维护或 binary search）
  - `PlayerManager.TeamPlayers` (`Dictionary<int, ClubPlayer>`) — 运行时阵容表
  - `PlayerAppearanceTable.dataByid` (`Dictionary<int, int>`) — 外观根据 player_id 动态查询
- **ID 边界**:
  - `public const int MinFakePlayerId = 300000` (假人从 300000 开始)
  - `public const int UserPlayerId = 1` (自创玩家 ID = 1)
  - 静态球员最大现有 ID: `175922`
  - **新 ID 安全区间**: `180000..299999`（完全避开静态 175922 和假人 300000）
- **结论**: **SAFE** (在 `180000..299999` 区间内，三表同步追加)

---

## 8. Step 3 Architecture (端到端数据流)

```
[Camera / Photo Album]
         │ (Image Bytes)
         ▼
[Face Processing] ──(Crop/Resize 256x256)
         │
         ▼
[EditablePlayerIcon.Save] ───────► ExternalDataArchives (Avatar Cache) [GREEN - API已确认]
         │
         ▼
[Custom Player Editor UI] ───────► UserPlayerSetupData [GREEN - 类结构确认]
 ├── Name (UTF-16)
 ├── Position (UIPosition 0..14)
 ├── 17 Attributes (balance..vision)
 ├── TeamId (targetTeamId)
 └── Appearance (skin/face/hair/head/eye/eyebrow/beard)
         │
         ▼
[Data Package Generator]
 ├── Players (plyrcsv0) ─────────► 追加 1 条 (ID 180000..299999) [GREEN - 已跑通]
 ├── ClubPlayer (17B) ───────────► 目标队追加 1 条 (UIRole) [GREEN - 已跑通]
 └── PlayerAppearanceTable (21B) ─► 索引表追加 (player_id, offset) [GREEN - 已跑通]
         │
         ▼
[Save/Load Pipeline] ────────────► ClubPlayerDatabase (Protobuf) [GREEN - 格式已确认]
         │
         ▼
[Win_PlayerCareer / Match] ──────► 游戏内渲染/比赛 [GREEN - Step 2A 已验证]
```

### 状态标注:
- **GREEN (已验证/结构完全确认)**:
  - 17 属性全定名与映射 (attr_00..16)
  - ClubPlayer UIRole 与 17B 布局
  - PlayerAppearanceTable 21B 字段
  - PlayerManager / allProto / ID 查找机制
  - UserPlayerSetupData 自创球员结构
  - EditablePlayerIcon 头像保存接口
  - gamedata 重打包与重签名 Pipeline
- **YELLOW (有代码证据，需 Step 3 实测)**:
  - `EditablePlayerIcon.Save(...)` 在真机环境下的外部文件落盘路径
  - 新增 ID (180000+) 在 `PlayerManager.getTemplateById` 二分查找时的排序要求
- **RED (Step 3 待开发)**:
  - 相机拍照/选图 Android 原生插件 (Activity/Intent)
  - 面部裁剪/缩放前处理
  - Custom Player 配置器 / 一键注入工具
