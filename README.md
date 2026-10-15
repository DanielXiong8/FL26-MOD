# FL26-MOD

a mod version of football league 2026, we recreated its database so that it is the same as current main clubs and leagues

（与 2026-27 赛季现实对齐的足球手游数据模改工程）

## 这个仓库是什么

对游戏数据库（1,858 支球队 / 52,640 名球员 / 37 个 UI 联赛）做全量"现实对齐"，并附带一整套逆向与工具链：

- **球员数据对齐（主线）**：28 个联赛组 / 476 支球队完成对齐 —— 真实姓名、转会、新援注入、离队删除、
  真实六维能力值（懂球帝数据源）、真实出生年份、国籍归一化。执行量：改名 5,955 / 转会 1,526 /
  注入 5,435 / 删除 3,771，全量一致性校验通过（全员有卡、有外观、无索引溢出）。
- **存读档工具链**：`SaveExport` / `SaveImport`（Android Activity，注入 dex 随游戏包运行），
  可整包导出/导入设备上的存档、配置文件（`player.dat` = UserSetting protobuf），用于研究游戏配置。
- **游戏配置与难度研究（进行中）**：IL2CPP 反汇编定位难度读写链路
  （`difficulty_selection` 远程开关、`CommonDifficulty`/`friendlyDifficulty` 本地键、
  `GenerateAIConfig` → `match_difficult` → `libfootball.so` 引擎），含代码级实验补丁记录。
- **捏脸管线（照片 → 游戏内 3D 脸）**：`work/face_pipeline`（烘焙/重光照/UV/外观注入脚本）+ FaceBuilder Web 应用源码。

## 目录结构

| 路径 | 内容 |
|---|---|
| `work/fc26_alignment/` | **主线**：对齐管线全部脚本与数据；`STATUS.md` = 完整项目手册（里程碑/坑/口径） |
| `work/face_pipeline/` | 捏脸管线（golden recipe 脚本、外观映射、IL2CPP 锚点） |
| `tools/saveexport/` | 存档导出/导入工具源码（Java + 编译好的 classes.dex），以及 `scripts/axml_add_activity*.py`（APK 注入工具） |
| `tools/FL26_FaceBuilderWeb/` | 捏脸 Web 应用（backend/frontend 源码） |
| `recon/02_engine/il2cpp/out/` | IL2CPP 反汇编分析产物（dump.cs / script.json / stringliteral.json） |
| `scripts/` | APK 打包与 AndroidManifest 注入脚本 |

## 主线流程（球员对齐）

```
db_survey.py            全库调查（Teams/Players/ClubPlayer/外观表 结构解码）
wiki_bulk.py            维基百科赛季页批量抓取 → squad_*.json
match3.py / plan_bulk.py 阵容匹配（姓氏评分 + 国籍 + OVR 审计）→ 转会/注入/删除计划
make_plan.py            合成 pl_plan.json（跨批次合并）
bulk_inject_pl.py       执行引擎：改名 / 转会 / 注入 / 删除 / 外观表追加 / 33 人上限重平衡
```

关键数据格式（`plyrcsv0` 球员表、`ClubPlayer` 17 字节成员表、外观表绝对偏移）见 `STATUS.md`。

## 存读档工具链

`tools/saveexport/src` → 编译（javac + d8）→ 得到 `classes10.dex` →
用 `scripts/axml_add_activity.py` 注入 APK（补 AndroidManifest 声明），然后：

```
adb shell am start -n <pkg>/com.fl26mod.saveexport.SaveExportActivity   # 导出到 /sdcard/Android/data/<pkg>/files/save_export
adb shell am start -n <pkg>/com.fl26mod.saveexport.SaveImportActivity   # 从 save_import/ 导入回 /data
```

## 反汇编分析

`recon/02_engine/il2cpp/out/` 为 Il2CppDumper 对本游戏 `libil2cpp.so` 的输出
（`global-metadata.dat` 版本 0.2.13）。`il2cpp.h` 与 `DummyDll/` 未收录（可用 Il2CppDumper 从游戏 APK 重新生成）。

## 本仓库不包含什么（重要）

- 不含游戏本体 APK、游戏素材/数据库文件（版权原因）
- 不含签名密钥（keystore）
- 不含任何设备存档、`player.dat`、个人 ID、照片与面部纹理
- 不含维基百科页面缓存（CC 授权内容，本地缓存不搬运）

## 声明

仅供个人学习与研究使用，请支持正版游戏。
