# FC26 对齐项目 — 状态与执行手册（2026-09-28）

## 任务
游戏数据库（1,858 队 / 52,640 人）与 FC26/现实 2026-27 赛季对齐：
名单同步（转会窗）、能力值更新、联赛归属修正。

## 已完成
1. **全库调查** `D:\FL26_Mod\work\db_survey.json`：
   - 107 原始分组 = **37 个 UI 联赛**（≥10 队）+ 68 碎组(1-9队) + 320 国家队 + 27 经典队
   - 结构全解：Teams(CSV col6=联赛键 col7=队名键)、strings(EN/ZH_CN 本地化)、
     Players(plyrcsv0 二进制：pid u32, name utf16, fa/fb/fc u16×3, nat u16, b1/b16/b0, attrs 17B, tail16, tail8, year u32)、
     ClubPlayer(sec1=team/count 8B对, sec2=17B: team u32, pid u32, jersey u32, f2=6912 u32, f3 u8)
   - 解析器复用：`tools/FL26_FaceBuilderWeb/backend/inject_player_v1.py`（parse_plyrcsv0/serialize_plyrcsv0）+
     `data_catalog.py`（Teams/strings/nations）
2. **采集通道测试**：
   - ✅ WebSearch（z.ai 服务端）：稳定，每队一次检索可得阵容摘要（英超 8 队试点完成，
     数据在本文件下方"已采集"节）
   - ✅ Wikipedia：本会话 WebFetch 成功过 2 次（Liverpool/Chelsea…），但本地网络间歇断连
     （shell 直连超时、代理 SSL 失败、WebFetch 间歇 ECONNRESET）
   - ✅ 懂球帝 dongqiudi.com：shell 可直连 (200)，但 team 页是 JS 壳 → 需逆向其阵容 API
     （页面 `dqd_test.html` 已存 work/ 目录；数据接口未解）
   - ❌ fifaindex 403；transfermarkt 405
3. **利物浦试点 gap**（`track_user1/liverpool_gap.json`）：
   - 20027=利物浦红（英格兰A级，29 人）≈ 2025-26 阵容（Wirts/Isac/Egitike/Frinpong 新援全在）
   - 缺 13 人 = 2026 夏窗（Barcola/Araújo租/Jacquet/Muñoz + Chiesa/Tsimikas 等回归）
   - 应删：M.Zalah(Salah 2026 离队)、Elliot(外租)
   - 游戏用谐音合法名：映射样例 A.Beckar=Alisson, Wirts=Wirtz, M.Zalah=Salah, Frinpong=Frimpong…
4. **能力值语义**：attrs 17B 未解码；样例 M.Zalah=[75,90,87,86,85,86,83,43],
   Vergil=[93,90,66,78,75,54,81,91] — 前 8 字节疑似六维+2，需用已知球星对照解码

## 已采集英超阵容笔记（8/20 队，WebSearch 摘要，部分不完整）
- Arsenal: Raya1,Kepa13,Meslier30,Setford35 | Saliba2,Mosquera3,White4,Hincapié5,Gabriel6,Timber12,Konsa15,Calafiori | Ødegaard8 | Saka7,Gyökeres14,Tzolis17,Madueke20
- Liverpool: 见 liverpool_gap.json
- Chelsea: Sánchez1,Penders13,Sharman-Lowe28,Slonina44 | Palestra2,Fofana3,Barco4,Lacroix5,Colwill6,Hato21 | Enzo8,Palmer10,Henderson14,Rogers17,Quenda23,Caicedo25,Lavia45 | Neto7,Gittens11,Estêvão41
- Tottenham: Xavi Simons7,Gallagher8,Maddison10,Archie Gray14,Bergvall,Tel11,Odobert28,Mudryk27(租),Kudus20,Robertson,Van Hecke,Senesi,Richarlison
- Newcastle: Pope1,Horníček21,Jaouen24,Gillespie29,Harris31 | Livramento2,Hall3,Botman4,Schär5 | Barnes11,Wissa9,Osula10,Touré15,Elanga19,Murphy23,Ramsey41,Willock28
- Man City: Donnarumma1,Bettinelli13,Rulli28 | Dias3,Guéhi6,Gvardiol24,Aït-Nouri21 | Kovačić8,Cherki10,Foden47,Doku11 | Haaland9,Ndiaye7,Allan37,Semenyo42
- Man United: Lammens,Darlow12,Heaton | Dorgu13,Dalot,De Ligt | Andrey Santos17,Tielemans18 | Rashford9,Cunha10,Zirkzee11,Mount7,Bruno8,Fletcher39
- Bournemouth: Petrović1,Araujo2,Truffert3,Hill5,Soler6,Aarons28,Milosavljević44 | Cook4 | Evanilson,Kluivert,Adli,Kroupi,Jebbison,Á.Rodríguez,Rayan

## 待执行（下一阶段）
1. **数据源定案**（三选一）：
   a. 懂球帝 API 逆向（shell 直连，最适合批量 1858 队）
   b. WebSearch 批量（稳定但每队一次工具调用，长跑需 automation）
   c. Wikipedia WebFetch（网络稳定窗口期跑批）
2. 谐音名匹配表：真名↔游戏名，52640 人，建议 Levenshtein+国籍+位置约束，分联赛人工抽验
3. attrs 17B 语义解码：对照 sofila 已知数值反推（Vergil/Salah/M.Zalah 样例已存）
4. 注入执行：缺员注入（inject_player_v1 公式已验证）+ attrs 更新（16 进制定位）
   + ClubPlayer sec1/sec2 同步 + 离队删除
5. 验证：注入后重跑 survey_db.py 对比

## 关键文件
- 全库调查: work/db_survey.json
- 调查脚本: work/face_pipeline/track_user1/survey_db.py
- 利物浦 gap: work/face_pipeline/track_user1/liverpool_gap.json
- 懂球帝样本: work/dqd_test.html
- 本队 base: build/base_debuggable2.apk（gamedata 未污染 ✓）


---
## 更新（2026-09-28 晚）：英超采集完成 + gap 报告
- **squad_pl_full.json**：20/20 队完整阵容（Wikipedia 抓取，含号码/位置）
- **pl_gap_report.json**：与游戏库模糊匹配结果
  - 匹配 189 | **真缺员 97** | 待核 155（extras：谐音名误判+青年队+旧将）
  - 缺员 Top：WestHam 14、CrystalPalace 13、Liverpool 11、Coventry 11、Forest 8、Bournemouth 7、Fulham 7
- 第二轮修正：KNOWN_PAIRS 人工对表已修 4 对（Vergil=VVD 等）；**下一步：把已知谐音名做成完整映射表再重跑**
- 游戏 20 队定位：20026-20031/20032-20050/20367/20311/20313/20324/20398
- 注入时注意：10059 中国队容已满 33（测试球员），游戏 team 10027 等可用


---
## 里程碑（2026-09-28 深夜）：英超更新包全链路打通 + 装机
**全链路验证完成**：调查 → 采集(Wikipedia) → 匹配(189对) → OVR解码([1]=OVR 实锤) → 清单(97缺员) → **注入 gamedata（Players 52640→52737, ClubPlayer 46515→46612, 复验通过）** → 构建 fl26_pl_update.apk → **adb install Success (设备 95e2d9a)**

**利物浦 20027 新名单实测（40 人）**：Araújo #23 OVR85 / Barcola #31 OVR84 / Tsimikas #21 OVR76 / Jacquet #20 / Muñoz #29 / Jarós #13 / Davies #16 / Chambers #24 / McConnell #27 / Koumas #32 / Danns #33 ✓ 全部就位

**关键脚本**（均在 fc26_alignment/）：
- make_manifest.py（gap报告+OVR字典→pl_update_manifest.json）
- bulk_inject_pl.py（plyrcsv0+ClubPlayer 17B 写回 → build/gamedata_pl.unity3d）
- APK 构建：zip 替换 gamedata + zipalign + apksigner（fl26_pl_update.apk, 441MB）

**真机验收注意**：Archives 只在首启导入 gamedata → 需 pm clear（清存档）后才能看到新名单；或用户决定。

**下一步**：
1. 真机验收（pm clear 后看利物浦/曼城/西汉姆新名单）
2. 189 在册 OVR 更新（清单已备，byte[1] 直接改）
3. 离队删除（155 待核分拣）
4. 其余 36 联赛铺开（同流程；采集换更快通道——本机 WebFetch 已恢复可用）
# FC26 对齐项目 — 状态与执行手册（2026-09-28）

## 任务
游戏数据库（1,858 队 / 52,640 人）与 FC26/现实 2026-27 赛季对齐：
名单同步（转会窗）、能力值更新、联赛归属修正。

## 已完成
1. **全库调查** `D:\FL26_Mod\work\db_survey.json`：
   - 107 原始分组 = **37 个 UI 联赛**（≥10 队）+ 68 碎组(1-9队) + 320 国家队 + 27 经典队
   - 结构全解：Teams(CSV col6=联赛键 col7=队名键)、strings(EN/ZH_CN 本地化)、
     Players(plyrcsv0 二进制：pid u32, name utf16, fa/fb/fc u16×3, nat u16, b1/b16/b0, attrs 17B, tail16, tail8, year u32)、
     ClubPlayer(sec1=team/count 8B对, sec2=17B: team u32, pid u32, jersey u32, f2=6912 u32, f3 u8)
   - 解析器复用：`tools/FL26_FaceBuilderWeb/backend/inject_player_v1.py`（parse_plyrcsv0/serialize_plyrcsv0）+
     `data_catalog.py`（Teams/strings/nations）
2. **采集通道测试**：
   - ✅ WebSearch（z.ai 服务端）：稳定，每队一次检索可得阵容摘要（英超 8 队试点完成，
     数据在本文件下方"已采集"节）
   - ✅ Wikipedia：本会话 WebFetch 成功过 2 次（Liverpool/Chelsea…），但本地网络间歇断连
     （shell 直连超时、代理 SSL 失败、WebFetch 间歇 ECONNRESET）
   - ✅ 懂球帝 dongqiudi.com：shell 可直连 (200)，但 team 页是 JS 壳 → 需逆向其阵容 API
     （页面 `dqd_test.html` 已存 work/ 目录；数据接口未解）
   - ❌ fifaindex 403；transfermarkt 405
3. **利物浦试点 gap**（`track_user1/liverpool_gap.json`）：
   - 20027=利物浦红（英格兰A级，29 人）≈ 2025-26 阵容（Wirts/Isac/Egitike/Frinpong 新援全在）
   - 缺 13 人 = 2026 夏窗（Barcola/Araújo租/Jacquet/Muñoz + Chiesa/Tsimikas 等回归）
   - 应删：M.Zalah(Salah 2026 离队)、Elliot(外租)
   - 游戏用谐音合法名：映射样例 A.Beckar=Alisson, Wirts=Wirtz, M.Zalah=Salah, Frinpong=Frimpong…
4. **能力值语义**：attrs 17B 未解码；样例 M.Zalah=[75,90,87,86,85,86,83,43],
   Vergil=[93,90,66,78,75,54,81,91] — 前 8 字节疑似六维+2，需用已知球星对照解码

## 已采集英超阵容笔记（8/20 队，WebSearch 摘要，部分不完整）
- Arsenal: Raya1,Kepa13,Meslier30,Setford35 | Saliba2,Mosquera3,White4,Hincapié5,Gabriel6,Timber12,Konsa15,Calafiori | Ødegaard8 | Saka7,Gyökeres14,Tzolis17,Madueke20
- Liverpool: 见 liverpool_gap.json
- Chelsea: Sánchez1,Penders13,Sharman-Lowe28,Slonina44 | Palestra2,Fofana3,Barco4,Lacroix5,Colwill6,Hato21 | Enzo8,Palmer10,Henderson14,Rogers17,Quenda23,Caicedo25,Lavia45 | Neto7,Gittens11,Estêvão41
- Tottenham: Xavi Simons7,Gallagher8,Maddison10,Archie Gray14,Bergvall,Tel11,Odobert28,Mudryk27(租),Kudus20,Robertson,Van Hecke,Senesi,Richarlison
- Newcastle: Pope1,Horníček21,Jaouen24,Gillespie29,Harris31 | Livramento2,Hall3,Botman4,Schär5 | Barnes11,Wissa9,Osula10,Touré15,Elanga19,Murphy23,Ramsey41,Willock28
- Man City: Donnarumma1,Bettinelli13,Rulli28 | Dias3,Guéhi6,Gvardiol24,Aït-Nouri21 | Kovačić8,Cherki10,Foden47,Doku11 | Haaland9,Ndiaye7,Allan37,Semenyo42
- Man United: Lammens,Darlow12,Heaton | Dorgu13,Dalot,De Ligt | Andrey Santos17,Tielemans18 | Rashford9,Cunha10,Zirkzee11,Mount7,Bruno8,Fletcher39
- Bournemouth: Petrović1,Araujo2,Truffert3,Hill5,Soler6,Aarons28,Milosavljević44 | Cook4 | Evanilson,Kluivert,Adli,Kroupi,Jebbison,Á.Rodríguez,Rayan

## 待执行（下一阶段）
1. **数据源定案**（三选一）：
   a. 懂球帝 API 逆向（shell 直连，最适合批量 1858 队）
   b. WebSearch 批量（稳定但每队一次工具调用，长跑需 automation）
   c. Wikipedia WebFetch（网络稳定窗口期跑批）
2. 谐音名匹配表：真名↔游戏名，52640 人，建议 Levenshtein+国籍+位置约束，分联赛人工抽验
3. attrs 17B 语义解码：对照 sofila 已知数值反推（Vergil/Salah/M.Zalah 样例已存）
4. 注入执行：缺员注入（inject_player_v1 公式已验证）+ attrs 更新（16 进制定位）
   + ClubPlayer sec1/sec2 同步 + 离队删除
5. 验证：注入后重跑 survey_db.py 对比

## 关键文件
- 全库调查: work/db_survey.json
- 调查脚本: work/face_pipeline/track_user1/survey_db.py
- 利物浦 gap: work/face_pipeline/track_user1/liverpool_gap.json
- 懂球帝样本: work/dqd_test.html
- 本队 base: build/base_debuggable2.apk（gamedata 未污染 ✓）


---
## 更新（2026-09-28 晚）：英超采集完成 + gap 报告
- **squad_pl_full.json**：20/20 队完整阵容（Wikipedia 抓取，含号码/位置）
- **pl_gap_report.json**：与游戏库模糊匹配结果
  - 匹配 189 | **真缺员 97** | 待核 155（extras：谐音名误判+青年队+旧将）
  - 缺员 Top：WestHam 14、CrystalPalace 13、Liverpool 11、Coventry 11、Forest 8、Bournemouth 7、Fulham 7
- 第二轮修正：KNOWN_PAIRS 人工对表已修 4 对（Vergil=VVD 等）；**下一步：把已知谐音名做成完整映射表再重跑**
- 游戏 20 队定位：20026-20031/20032-20050/20367/20311/20313/20324/20398
- 注入时注意：10059 中国队容已满 33（测试球员），游戏 team 10027 等可用


---
## 里程碑（2026-09-28 深夜）：英超更新包全链路打通 + 装机
**全链路验证完成**：调查 → 采集(Wikipedia) → 匹配(189对) → OVR解码([1]=OVR 实锤) → 清单(97缺员) → **注入 gamedata（Players 52640→52737, ClubPlayer 46515→46612, 复验通过）** → 构建 fl26_pl_update.apk → **adb install Success (设备 95e2d9a)**

**利物浦 20027 新名单实测（40 人）**：Araújo #23 OVR85 / Barcola #31 OVR84 / Tsimikas #21 OVR76 / Jacquet #20 / Muñoz #29 / Jarós #13 / Davies #16 / Chambers #24 / McConnell #27 / Koumas #32 / Danns #33 ✓ 全部就位

**关键脚本**（均在 fc26_alignment/）：
- make_manifest.py（gap报告+OVR字典→pl_update_manifest.json）
- bulk_inject_pl.py（plyrcsv0+ClubPlayer 17B 写回 → build/gamedata_pl.unity3d）
- APK 构建：zip 替换 gamedata + zipalign + apksigner（fl26_pl_update.apk, 441MB）

**真机验收注意**：Archives 只在首启导入 gamedata → 需 pm clear（清存档）后才能看到新名单；或用户决定。

**下一步**：
1. 真机验收（pm clear 后看利物浦/曼城/西汉姆新名单）
2. 189 在册 OVR 更新（清单已备，byte[1] 直接改）
3. 离队删除（155 待核分拣）
4. 其余 36 联赛铺开（同流程；采集换更快通道——本机 WebFetch 已恢复可用）


## v2（同夜）：FC26 OVR 校正并入
- 抽查 38 名在册球星：22 人 game OVR 与 FC26 精确一致（±1），16 人偏 2-5 → **游戏库≈FC26 但非全同，OVR 更新有意义**
- 44 条 ovr_update 带 FC26 真实值；**实际应用 16 处 byte[1] 校正**（其余已一致）
- 重建 fl26_pl_update.apk → install Success（设备 95e2d9a）
- 余:145 条 ovr_update 待补 FC26 数值（需可扩展的评分数据源）；155 离队待分拣；36 联赛待铺开

---
## 里程碑（2026-10-02）：3 步对齐引擎上线（用户工作流落地）
**用户工作流**：①先把所有球员变成真名 → ②再分配到球队 → ③再改球队名字等信息。

**关键机制结论**：
- Players(plyrcsv0) 每 pid 一条 name → **改名=按 pid 全局改**（同一人俱乐部+国家队同步变真名）。
- **同名字符串≠同一人**：如 `Fernandez` 在 41 队被复用（不同 pid）→ 改名必须按 (俱乐部,名)→pid 解析，**严禁按名字字符串全局改**。
- "球队没有的球员"（如利物浦没有巴尔克拉）分两类：
  - **库里已有（谐音名在别队）→ 转会**：改 pid 的 ClubPlayer 归属（只动俱乐部归属，国家队归属保留）+ 真名 + 真实号码 + OVR。实例：Barcora(巴黎)→Bradley Barcola 利物浦#29、Tsimikars(罗马)→#21、R.Alaojo(巴萨)→Araujo #33、Ganacho(切尔西)→Garnacho 维拉#9、Chilweel(斯特拉斯堡)→Chilwell 水晶宫#33、Kalimendo(法兰克福)→Kalimuendo 森林#15、Araujo(墨西哥城)→伯恩茅斯#2。
  - **库里真没有 → 注入新 pid**（模板属性+OVR+号码冲突避让）。
- Teams 的 `Real_*` strings 已是正确英文队名（Real_EnglishA_Chelsea="Chelsea"）→ 步骤③队名基本免做；联赛归属修正（英超20队 vs 库里57队混编）留待铺开阶段。

**本轮执行（build_pl_align.py，从干净 db_survey_gamedata.unity3d 重建）**：
- STEP1 改名 198/198（188 权威匹配 + 7 转会源 + 3 离队者；按 pid）
- STEP2 OVR 修正 23（ovr_fc26 已知值，先改名前应用——顺序坑已修）
- STEP2 离队 3（利物浦：Salah/Konate/Robertson 移除归属，记录保留）
- STEP2 转会 7/7（真实号码 #21/#33/#29；转会后巴黎/巴萨/罗马/切尔西均失去该员，国家队保留）
- STEP2 注入 90（pid 175923..176012）
- 校验：Players 52640→52730(+90)，sec2 46515→46602(+87=+90-3) ✓
- **产物：build/fl26_pl_align.apk（441,579,952B，签名 OK）**；装机未成（设备 95e2d9a 离线）→ 待设备在线 `adb install -r` + `pm clear`。

**利物浦 20027 复验（37 人）**：真名全覆盖；11 新援全部就位；Salah/Konate/Robertson 已移除；租借/青训保留（Joonz/Elliot/A.Pecsy/Baitetic/R.Willians/Ramsey 留用，真名未猜）。

**保守原则**：目标名单为一线队部分名单 → 只增不删（除确认离队）；不确定的谐音名不猜（宁留原名）。

**脚本链**：build_alias.py(189权威) → make_plan.py(pl_plan.json: RENAME/TRANSFER/INJECT/REMOVE) → build_pl_align.py(引擎) → build_apk_pl2.py(APK)。调试脚本：audit_twins/clean_transfer_audit（转会审计含误报， Curated 手核为准）。

**下一步**：
1. 设备在线 → install + pm clear → 真机验收利物浦
2. 其余 19 队同引擎铺开（先补齐 7 队无 gap 报告的：热刺/曼城/曼联/纽卡/伊普斯维奇/赫尔/桑德兰）
3. 其余 36 联赛 + 国家队（同 3 步引擎，Wikipedia 采集→别名→计划→执行）
4. 离队分拣扩容（155 extras 逐队核真伪）+ 联赛归属修正（英超 20 队 vs 57 队混编）

---
## 里程碑（2026-10-02 深夜）：v2 全 20 队对齐 + 装机成功
**fl26_pl_align.apk 已 install Success（设备 95e2d9a 在线）**。查看新名单需 pm clear（清存档，用户决定）。

**本轮扩充**（propose_pairs.py 提案 + 逐项人工核定）：
- 同队漏配修复 30 对（如 Haaland↔Harland、Pope↔Pop、Gray↔Graey、Doku↔Douku、Ballard↔Ballowd、Xhaka↔Zhaka、Sarr↔Sal、Schade↔Schader、Keane↔Keen、Berge↔Belge…），**转会后同队漏配=误删风险的主要来源**
- 新转会 22 笔（共 29）：Robertson 利物浦→热刺、van Hecke 布莱顿→热刺、Senesi 伯恩茅斯→热刺、Mudryk 切尔西→热刺、Santos 切尔西→曼联、Rashford 巴萨→曼联、Lacroix 水晶宫→切尔西、Harwood-Bellis 南安普顿→维拉、Muñoz 水晶宫→森林、Diomande 科特迪瓦国家队→森林（首个 NT 源转会：改真名+保留国家队籍+加俱乐部）、Morato/Veltman→西汉姆、Danso 热刺→桑德兰、Iroegbunam 埃弗顿→赫尔、Lukić 富勒姆→伊普斯维奇、Awoniyi/Hamer/Bentley→考文垂、Konsa 维拉→阿森纳、Disasi/McNeil→水晶宫、Engels 流浪者→西汉姆
- 7 队全量处理（热刺/曼城/曼联/纽卡/伊普斯维奇/赫尔/桑德兰）：同队 keep + 注入（注入带真实国籍 84 国）
- 转会 ovr=None → 保留源卡能力值（游戏本就是 FC26 世代数值）；球衣号三段分配（目标号空闲优先→源号→递补）

**执行计数**：RENAME 317 / TRANSFER 29 / INJECT 116 / REMOVE 2；Players 52640→52756(+116)，sec2 46515→46629(+114=+116-2) 复验✓

**坑与修复**：
- exec(make_manifest) 重生成 manifest → 丢 44 条 ovr_fc26（STEP2a=0）；本轮接受（游戏原值已 FC26），后续如需再补估值表
- JERSEY_USED 快照导致转会球衣级联冲突 → 改实时计算+两阶段（先删全源再分配）
- spam 替换补丁 whitespace 不匹配会静默失败 → 补丁后必须 grep 验证
- Bergval 同队双 pid（数据伪影）→ 取 OVR 高者改名

**真机验收（待用户）**：pm clear com.football.soccer.league.mod → 看利物浦/热刺/曼城/森林名单。
**下一步**：其余 36 联赛同管线铺开（采集→CLUB_FIXES/TRANSFERS 人工核→make_plan→引擎）；155 extras 离队分拣；联赛归属修正（英超20 vs 库里57）。

---
## 里程碑（2026-10-02 深夜 2）：西甲 20 队对齐完成 + v3 装机 Success
**采集**：squad_laliga.json 20/20（赛季页+小俱乐部主页；豪门主页会截断→用 2026-27 season 页）。
**现实西甲 20 队**（升：Racing/Deportivo/Málaga；降：Oviedo/Girona/Mallorca）→ 游戏 tid 映射 20101-20123/20301/20304/20396。
**管线**：laliga_match1.json 严格自动匹配(≥0.72+号码加分) → 人工核定（拒 5 泛用名对）→ CLUB_FIXES 补救 30+ 对（Sevilla/Levante/Malaga 重灾区）→ 43 转会（含 13 西甲+跨联赛：Cucurella/Bernardo→皇马、G.Jesus/Rodri/Gordon→巴萨、Romero→马竞、Bayındır 曼联→塞尔塔、Ünal 伯恩茅斯→赫塔菲、Gudelj/Ceballos→贝蒂斯、V.Munoz 潘普洛纳→利物浦 [Osasuna 页实锤 €40m]）+ ATTACH 新操作（Konaté 离队后自由身入皇马 #25——离队≠消失）。
**执行**：RENAME 607 / TRANSFER 43 / ATTACH 1 / INJECT 298 / REMOVE 2；Players 52640→52938(+298)，sec2 46515→46812(+297) 复验✓ → fl26_pl_align.apk install Success（95e2d9a）。
**注入国籍**：西甲默认 Spain + NAT_EX 例外 100+ 国（与 nations 表运行时校验，缺省回落）。
**已知残留（可接受 v1）**：球衣号冲突时兜底号（留队 extras 占号）；Sevilla 41 人臃肿（旧 extras 未删）；租借球员按"留母队"处理（游戏无租借态）；英超↔西甲间更多暗线转会待德意法联赛采集后浮出。
**坑**：同club双同名（Trufert×2/Bergval×2）取OVR高者；str.replace 补丁遇 CRLF/近形锚点会静默失败——**行级插入+grep 验证**成为标准做法；make_manifest 不可 exec（会重写 manifest）。
**下一步**：德甲（CompName_GermanLeagueA）/意甲/法甲同流程；155 英超 extras 离队分拣；联赛归属修正。

---
## 里程碑（2026-10-03）：德意法批量管线 + v4 装机 Success
**批量通道**：curl(10808代理)+Wikipedia API 一次5队拉全量 wikitext（56 队 23 秒），解析 {{Fs player|no|pos|nat|name}} → squad_bundesliga/seriea/ligue1.json（1,381 人全带国籍）。
**匹配器 v3**：分词姓氏评分（norm 前分词！），泛用姓需号码+0.9 阈值；685 对同队 keep。
**严格转会审计**：姓 sim≥0.78 + 国籍精确 + OVR≥60 + 全库唯一 → 208 笔自动转会（如 Saibari→拜仁、Karetsas→多特、Doué→勒沃库森、Raum 国家队卡→莱比锡）。同队改名型转会（Kobel）无害。
**执行 v4**：RENAME 1489 / TRANSFER 248 / ATTACH 1 / INJECT 786 / REMOVE 2；Players 52640→53426(+786)，sec2 46515→47300(+785) 复验✓ → fl26_pl_align.apk install Success（95e2d9a）。
**覆盖**：英超/西甲/德甲/意甲/法甲 五大联赛 98 队 2026-27 对齐完成。
**坑**：wiki_bulk nat 字段是 |nat= 不是 |nationality=；norm 先去空格导致分词失效（先分词后归一）；维基名带 (footballer) 消歧后缀须剥除。
**剩余 30+ 小联赛**：管线已全自动化（league_tids.json + 队名页清单 + bulk fetch + plan_bulk），每联赛约 10 分钟；待后续会话按 same 流程铺开（葡/荷/土/苏/比/巴西/阿/美/墨/沙特/日/韩…）。

---
## 里程碑（2026-10-03 凌晨）：阵容空场破案 + 存档库解剖
**症状**： lineup editor 只剩门将在场+一张 99-FC"2222222222"假人卡（跨队相同=游戏无效成员占位）。
**破案路径**（二分法+存档解剖）：控制组（零改动重打包）完美 → 改名-only 完整比赛 ✓ → 注入-only ✓ → 转会+删除 ✓ → 转会+删除+771注入 = 复现崩坏。
**存档解剖**（SaveExportActivity 导出 Archives/*.db）：game 阵容 UI 读分赛事 sqlite 库（SimpleClub/CompName_EnglishLeague.db 等，protobuf blob：team_blob=每队自动选的首发11人(player,slot)，player_blob=(pid,field2,7731,OVR)）。坏档特征=部分球员 payload 丢 field2（对照包全员都有）→ UI 遇缺字段成员中止渲染。
**根因**：转会/删除在 ClubPlayer f2 槽位（=256×slot）留洞+注入全堆 27 号 → 导入器派生 field2 失败。
**修复**：出包前每队槽位连续重编号（0,1,2,…×256）。
**重大操作事故（教训）**：为导存档叠加 saveexport 底包（含原始 gamedata）→ 用户打开游戏时按原始数据重导 → 名单全回原样（用户报告"利物浦没有变更/没有巴尔克拉"）。**铁律：saveexport 包只做导出工具，导完立刻换回对齐包；任何时刻 pm clear+重导都必须发生在对齐包安装状态下。**
**验证顺序**：pm clear → 启动等 240s 完整导入 → overlay saveexport 导出 → 校验 English DB（tables=4, players=1889=1838+115注入−64离队转出 ✓）→ overlay 对齐包（-r 保数据）→ 交用户验收。

---
## 里程碑（2026-10-03 晨）：脸模丢失+年龄错误破案修复
**脸模丢失根因**：base PA 表的 idx offset 是**绝对文件偏移**（含 4B count+idx 区，首条=427340），且数据区含 306 条索引外的尾随记录（52952×21 vs 52646 条）。重构注入器时把 t_app 切片当数据区相对偏移 → 模板记录在表尾的注入卡切到空字节（~164 条整条丢失、全部偏移雪崩）→ 无脸。**修复=t_app 用 pa_raw[绝对偏移+4:+21]（与已验证 v1 一致）**，并加不变量：PA idx offset-overflow=0、注入卡 app 全 17 字节。
**年龄修复**：fetch_births.py——重解析缓存的俱乐部页保留原始 wiki 标题（含消歧后缀）→ API 批量抓（重试+generator=search 兜底）→ 381/619 注入卡写入真实出生年（其余 238 无词条青训，暂用模板年）。
**装机验收链**（防原始包覆盖事故）：对齐包 → pm clear → 启动 240s 完整导入 → overlay saveexport 导出校验（english 1889、注入入库 115/115 ✓）→ **换回对齐包（-r 保数据）** → 交用户。全链绿灯。

---
## 里程碑（2026-10-04）：11 联赛 198 队版本装机
**新增六联赛**：葡超18/荷甲17/土超16/比甲18/苏超12/巴甲19（现实2026-27成员从联赛页 locations 表提取，桶配映射按城市+颜色+球员名交叉验证：Celtic=20211 格拉斯哥(Engels 实证)、Rangers=30117 蓝、Marítimo=丰沙尔RG、Botafogo=里约黑白、Palmeiras=圣保罗 绿…）
**执行**：RENAME 2662 / TRANSFER 637 / INJECT 1982 / REMOVE 1407 / ATTACH 1；Players 54622(+1982)，sec2 47091(+576)，PA 54628 条零溢出；birth years 741/1620。
**存档机制新认知**：league 分库（SimpleClub/CompName_*.db）在生涯流程进入该联赛时才创建（fresh save 只有 friendly/static；fresh friendly player_blob=26 与对照一致=正常态）；**首启导入验证只看 friendly/static**。saveexport 叠加包导致的空英联赛库=无人生涯进过英超，非故障。
**装机完成**：fl26_pl_align.apk（对齐 gamedata）+ 对齐存档在机。待用户验收：利物浦/波尔图/费耶诺德/加拉塔萨雷/弗拉门戈 名单+阵容页+脸模+年龄。

---
## 里程碑（2026-10-04）：19 联赛 342 队版本装机
**新增八联赛**：阿甲27/墨超17/沙特12/日J18/韩K12/中超16/MLS26/俄超16（城市+颜色+球员名映射；J1 页面用 {{football squad player}} 模板 → wiki_bulk 已支持双模板）。
**执行**：RENAME 4631 / TRANSFER 1028(计划1123，95笔因源员先被33人上限淘汰而落空——下版应把 rebalance 移到 transfers 之后) / INJECT 3743(pid 至 179665) / REMOVE 2725 / ATTACH 1；Players 56383(+3743)，sec2 47534(+1019)，PA 56389 零溢出。birth years 1122/3743（剩余 2621 待增量补，fetch_births 受 API 限流中途中止，已有数据保留）。
**装机链**：build → pm clear → 480s 导入 → friendly(28/1862) 校验 ✓ → 换回对齐包。
**覆盖**：19 联赛 342 队（英西德意法葡荷土比苏巴阿墨沙特日韩中MLS俄）。剩余 ~20 联赛组待铺。

---
## 里程碑（2026-10-04 下午）：数据质量审计 + 三项修复 + 装机
**审计发现（对 3,743 注入卡）**：
1. 国籍：723 人回落 England——双根因：游戏国名表为下划线风格（South_Korea/China/United_States…）而映射用空格；FIFA 码表缺 27 键（CHE/CHL/PRY/SER/SLO/NGR/BLR/KAZ…）+ 部分行 nat 直接是全名。
2. OVR：3,644 人=默认 70（plan_bulk 旧默认），Rafael Leão(加拉塔萨雷) 70 级完全失真。
3. 年龄：仅 747/3,743 有真实出生年（API 限流，fetch_births 两轮中止）。
**修复**：①引擎 nat_idx 下划线/空格归一；②FIFA 补 27 键 + 行值允许全名直传；③plan_bulk 每联赛默认国籍（Brazil→Brazil 等）；④注入 OVR 改为俱乐部在册球员中位数（match 报告 pairs 统计）；⑤三批 extras 全部重生成。
**装机**：19 联赛版本重启导入 ✓（主菜单正常；黑屏阶段=导入+赛程模拟，为正常态；英联赛库 1,861 人/71 队建库 ✓）。Rafael Leão→加拉塔萨雷 为真实签约非误配。
**残留**：2,900+ 注入卡年龄仍为模板年（API 限流待续抓）；OVR 为俱乐部中位近似而非真实 FC26 值；95 笔转会因 rebalance 顺序落空（下版 rebalance 后置）。

---
## 里程碑（2026-10-04 晚）：真实六维接入 + 装机 Success
**attrs 17B 六维映射破译**（8 球星锚点交叉验证，avgΔ≤6）：[0]=PHY [1]=OVR(非SHO!) [2]/[3]=PAC [4]/[11]/[12]/[16]=PAS [5]/[9]/[10]=DRI [6]/[13]/[14]=SHO [7]/[8]/[15]=DEF。
**数据源**：懂球帝（国内直连免代理）——search API(api.dongqiudi.com/search) + 球员页服务端渲染雷达（综合能力+速度/力量/防守/盘带/传球/射门）。**中文搜索一发入魂（英文搜姆巴佩命不中）；候选=token 重叠+出生年核对**。
**落地**：1,405/3,743 注入卡写入真实六维+OVR+出生日期（GK 保留模板属性只写 OVR；青训无雷达者用俱乐部中位）。fetch_dqd2.py 可续跑（每 40 名落盘一次）。
**装机**：fl26_pl_align.apk（真实六维版）+ pm clear + 480s 导入 + friendly(26/1862)✓ + 对齐包归位。**READY**。
**残留**：2,324 注入卡六维缺失（懂球帝无页/限流，续跑补）；OVR=懂球帝综合与 FC26 略有出入属正常。

---
## 里程碑（2026-10-05）：转会源卡去重 + 真实六维版终装机
**新破案**：95 笔转会失败根因=**两名真实球员（如 Gonçalo/Miguel Nogueira 兄弟）的审计各自命中同一张游戏卡**——前者转会移走后后者失源。修复=plan_bulk 全局 claimed_pids 集合（一卡只认领一次，落选者改注入）。
**终版执行**：RENAME 4659 / TRANSFER 1064 / INJECT 3800 / REMOVE 2719 / ATTACH 1；Players 56440(+3800)、PA 零溢出、members 47597 全有卡+全有外观。
**数据质量**：六维真实值 1,405+ 人（懂球帝，映射 [0]PHY[1]OVR[2/3]PAC[4/11/12/16]PAS[5/9/10]DRI[6/13/14]SHO[7/8/15]DEF）；birth 741+wikipedia+dob 双源；国籍下划线归一+27 补码；OVR=懂球帝综合(有数据)/俱乐部中位(无数据)。
**装机**：fl26_pl_align.apk 装机+对齐存档重导验证（friendly 4 表/26 人 ✓）+ 对齐包归位。READY。
**待办**：续跑 fetch_dqd2 补 2,300+ 人六维；剩余 ~20 联赛组铺开。

---
## 里程碑（2026-10-05 下午）：+英冠批次 = 20 联赛 366 队装机
**新增**：2026-27 英冠 21 队（伯明翰/布莱克本/博尔顿/布城/伯恩利/卡迪夫/德比/米堡/诺维奇/朴茨茅斯/普雷斯顿/QPR/谢联/南安普顿/斯托克城/斯旺西/沃特福德/西布朗/西汉姆(降级!)/狼(降级!)/雷克斯汉姆）。发现：二级队与顶级队共用 league_key（英格兰 57 队混编 A 组），无需新建联赛。
**执行**：RENAME 5010 / TRANSFER 1135 / INJECT 4031 / REMOVE 2887；Players 56671(+4031)、PA 56677 零溢出、members 47660 全有卡+全有外观 ✓。
**装机**：fl26_pl_align.apk + 清档重导（friendly 4表/28人 ✓）+ 对齐包归位。READY。
**注**：西汉姆/狼队 2026-27 从英超降级（维基实证），已随英冠批对齐。

---
## 里程碑（2026-10-05 下午2）：+德乙/意乙/法乙/西乙批次 = 24 联赛 414 队装机
**新增**：德乙16（含沃尔夫斯堡降级!）/意乙12（含桑普多利亚、维罗纳降级）/法乙15（含圣埃蒂安、南特、蒙彼利埃降级）/西乙2（赫罗纳降级、特内里费）。西乙页只解析出 4 队（表格格式不同，其余待补）。
**执行**：RENAME 5527 / TRANSFER 1314 / INJECT 4557 / REMOVE 3243；Players 57197(+4557)、PA 57203 零溢出、members 47830 全有卡+全有外观 ✓。
**装机**：fl26_pl_align.apk + 清档重导（friendly 4表/28人 ✓）+ 对齐包归位。READY。
**覆盖**：24 联赛组 414 队。待铺：西乙主体+更多低级组；六维续抓 2,300+。

---
## 里程碑（2026-10-05 晚）：+西乙主体 = 25 组 436 队装机
**新增**：西乙 22 队（阿尔巴塞特/阿尔梅里亚/安道尔/布尔戈斯/加的斯/科尔多瓦/埃瓦尔/赫罗纳(降级)/格拉纳达/莱内加斯/马略卡/奥维耶多/希洪/巴利亚多利德/特内里费/拉斯帕尔马斯/韦斯卡/米兰德斯/萨拉戈萨/桑坦德竞技/马拉加/费罗尔）。西乙页 Clubs 在 Location map 的 label 里（非标准行表）→ 解析器已适配。
**执行**：RENAME 5733 / TRANSFER 1398 / INJECT 4853 / REMOVE 3437；Players 57493(+4853)、PA 57499 零溢出、members 47932 全有卡+全有外观 ✓。
**装机**：对齐包+清档重导（friendly 4表/27人 ✓）+对齐包归位。READY。
**注意**：pull 相对路径坑——必须在 work/fc26_alignment 目录下执行（否则 Git Bash 把 /sdcard 转成 C:/Program Files/Git/...）。

---
## 里程碑（2026-10-05 晚2）：+荷乙/巴乙批次 = 27 组 458 队装机
**新增**：荷乙 13 队（维特斯/瓦尔维克/阿尔默洛/布雷达/多德雷赫特/罗达/登博斯/埃门/海尔蒙德/马斯特里赫特/奥斯/福伦达/芬洛）+ 巴乙 11 队（ América-MG/戈亚尼恩斯竞技/阿瓦伊/塞阿拉/CRB/克里西乌马/戈亚斯/隆德里纳/瑙蒂科/诺罗津蒂诺/蓬塔普雷塔）。土乙页 0 行（表格格式不同待适配）。
**执行**：RENAME 5852 / TRANSFER 1458 / INJECT 5198 / REMOVE 3620；Players 57838(+5198)、PA 57844 零溢出、members 48094 全有卡+全有外观 ✓。
**装机**：对齐包+清档重导（friendly 4表/26人 ✓）+对齐包归位。READY。
**注意**：后台抓取实例注意 python3.13.exe 进程名（tasklist/python taskkill 均需匹配）；多实例并发会互覆写 dqd_abilities.json。

---
## 里程碑（2026-10-06）：+土甲（TFF 1. Lig）批次 = 28 组 476 队装机
**新增**：土甲 18 队（开塞利/锡瓦斯/班德尔马/布尔萨/博德鲁姆/马尼萨/彭迪克/万斯珀/卡拉古姆鲁克/凯乔伦/博卢斯波/伊斯坦布尔士邦/乔尔姆/阿达纳迪美尔/萨卡里亚/代尼兹利/乌姆拉尼耶/萨勒耶尔）。TFF 页标题实际为 "2026–27 TFF 1. Lig"（搜索 API 定位）。位置图 label 支持粗体/链接/nowrap 混合格式解析。
**执行**：RENAME 5955 / TRANSFER 1526 / INJECT 5435 / REMOVE 3771；Players 58075(+5435)、PA 58081 零溢出、members 48180 全有卡+全有外观 ✓。
**装机**：对齐包+清档重导（friendly 4表/26人 ✓）+对齐包归位。READY。
**覆盖**：28 组 476 队。六维续抓 2,300+ 人进行中。

---
## 里程碑（2026-10-05 深夜）：难度失灵破案 + player.dat 补丁
**问题**：mod 后比赛难度滑条失效，任何档位 AI 都是 beginner 强度。
**排查**：①UnityPy 重打包字节往返验证=ChallengeConfig/AIPlayingStyleConfig/PlayerIngameRatingRules/ui_string 全部 byte-exact（配置没坏）；②难度标签=ui_string 的 difficulty_0..4（Beginner/Amateur/Normal/Professional/Top Player）；③联赛存档 team_blob/archive_blob 与全新档一致（难度不在联赛库）。
**真凶**：files_root/player.dat=游戏远程配置表（protobuf feature flags），其中 **difficulty_selection=false**（难度选择功能被服务器配置禁用）→ 比赛设置里选难度被忽略，AI 固定 beginner。时间上与 mod 装机重合纯属巧合（服务器下发配置变更）。
**修复**：①扩展 SaveImportActivity 源码（tools/saveexport/src）新增 save_import/files_root→files/ 和 save_import_files/player.dat→files/player.dat 两个导入路径，重编译只换 classes10.dex（mod 类所在 dex；**绝不可动 classes.dex=游戏主代码+androidx，换了 Firebase 崩+游戏全黑**）；②fix_difficulty.py 外科手术改 player.dat（difficulty_selection=true + new_dynamic_difficulty_rule=1）。
**装机验证**：设备 player.dat 已含 difficulty_selection=true ✓，对齐包归位。
**注意**：player.dat 是服务器下发配置，游戏联网启动可能重新覆盖。若被覆盖：①飞行模式启动测试（离线读本地配置）②MIUI 应用联网权限设为禁用 ③再跑一遍 fix_difficulty+import 流程。
**工具**：build/saveimport_tool3.apk=支持 files_root/player.dat 导入的导出工具（永久可用）。

---
## 里程碑（2026-10-10）：难度真根因=旧补丁自己就是坏的 + player.dat 结构全解 + 修正补丁导入
**真根因**：旧 fix_difficulty.py 的 protobuf 编辑有编码 bug——它把 key 后面的 field-2 TAG 字节（0x12）当成长度 varint 吃掉，产出 `field0/wiretype4` 非法 tag。Google.Protobuf 严格解析会在该处抛错，游戏拿不到 UserSetting 整表（CommonDifficulty 被重置为 0=Beginner），所以"补丁导入过、还是失灵"。
**证据**：严格解析对照——旧 `player_dat_fixed.bin` FAIL（invalid tag 0x01 at 29）/ 新 `player_dat_fixed3.bin` OK。
**player.dat 真结构（本次破译）**：`[16B 头（非校验和；同一用户跨 payload 不变）] + envelope{ f3 varint=1, f4=(UserSetting 序列化) }`；
UserSetting：f1 InstallVersion("0.2.13") / f2 LoginVersion / **f3 ABTest map<string,string>（设备当前 194 条，含 difficulty_selection）** / f4 EasyString map / **f5 EasyInt map（30 条，含 CommonDifficulty；proto3 零值省略→值为 0 时 entry 只有 key）** / f8 ButtonConfig / f11 DifficultyPopupSettings / f14 IAPDatas。
**难度管线（IL2CPP 反汇编 recon/02_engine/il2cpp/out/dump.cs + libil2cpp.so）**：
- `Win_DifficultyOption.IsEnabled → ABTest.EnableDifficultySelection → ReadBoolFromPrefs(difficulty_selection=184)`；
- 存储层 EasySave(FLUserSetting) = UserSetting 的 EasyInt/ABTest map（键 "friendlyDifficulty" / "CommonDifficulty"）；
- 读取：friendly 模式 → EasyInt['friendlyDifficulty']（缺省 0）; 联赛/杯赛 → IsEnabled 时先 archive 难度、否则 EasyInt['CommonDifficulty']；
- **SetDifficulty(matchManager,…) 受 IsEnabled 门控：flag=false 时用户选档不落盘 → 读回恒为默认 0 = "所有挡位都是 beginner"**。
**修正补丁**：`fix_difficulty3.py`（基于当前设备文件；9307→9306B；仅 ABTest['difficulty_selection']→'true'，0x12 tag 完好；其余 193 条 ABTest + 30 条 EasyInt 逐条核验不变）→ `player_dat_fixed3.bin`。
**设备落地**：push 至 save_import_files/player.dat → SaveImportActivity（日志 "player.dat imported, 9306B"）→ SaveExportActivity 导出回验 = **true ✓**（verify2/player_before.dat / player_after.dat）。
**待用户实测**：游戏内改难度档位后打一场（friendly + 联赛各一）。若联网启动被服务器覆写（difficulty_selection 回 false）→ 飞行模式/禁该应用联网后重导入。
**设备现状注意**：当前装的是**库存数据工具包**（421,428,623B=saveexport/import 系，lastUpdate 10-06 00:57），**对齐版 fl26_pl_align.apk（442,207,409B）未安装**——测试后需重装对齐版。
**工具链**：saveimport_tool3.apk 支持 import；saveexport_prefs（含 shared_prefs 导出）源码在 tools/saveexport/src 可随时重编译。

---
## 里程碑（2026-10-10 下午）：难度读数位置定案 + 设备状态修复（对齐包+工具合并装回）
**反汇编定案（libil2cpp.so 调用图扫描 + 逐函数反编译）**：
- `DifficultyMode` 枚举：Friendly=1, Club=2, Nation=3, Champion=4, Women=5；`MatchManagerType`：FACup=0, League=1, Friendly=2。
- `Win_DifficultyOption.GetDifficulty(manager)`：Friendly(1/type2) → `EasySave.GetInt("friendlyDifficulty", 0)`；其余 → [flag=true 时先试 TryGetArchiveDifficulty] 否则 `EasySave.GetInt("CommonDifficulty", 0)`，最后 Clamp(0,4)。
- 存储层 EasySave = **player.dat 的 UserSetting.EasyInt map**（客户端自有，服务器不同步）；ABTest map（含 difficulty_selection）是**服务器每次启动覆写**——所以不再对抗它，flag=false 时两条读路径照样可用。
- **真相**：用户历次调档其实都保存成功了（EasyInt['CommonDifficulty'] 在 10-04~10-10 的导出里留下过 3/4/3 的历史值）——"调了没用"的机制是：①**友谊赛读的是另一个键 friendlyDifficulty，从未被写过 → 恒默认 0=Beginner**；②联赛/杯赛读 CommonDifficulty 本应生效。
**设备状态事故（本轮回合发现）**：设备上装的是"库存数据工具包"（gamedata=原始假名数据，hash 12438ab7），而 /data 存档是 10-05 对齐版时代生成的——EnglishLeague.db 的 1940 名球员中 **346 名（17.8%）在库存包里不存在**（对齐注入的 175923+ pid）→ 联赛阵容残缺/对手偏弱，会污染难度观感。
**修复动作**：
1. `fix_difficulty4.py`（基于设备当前 9309B 文件）：新增 EasyInt 记录 `friendlyDifficulty=3`（0x10 varint 编码；全图表比对：ABTest 194 条零差异，EasyInt 30→31 仅新增）；导入设备并导出回验 ✓（9333B：difficulty_selection=false / CommonDifficulty=3 / friendlyDifficulty=3）。
2. **重建 APK = 对齐数据 + 工具类**：`scripts/axml_add_activity_aligned.py`（复用 axml_add_activity 逻辑：fl26_pl_align.apk + AndroidManifest 注入 2 个 exported activity + classes10.dex 15464B）→ zipalign → apksigner（fl26_test.keystore）→ **install -r（不清档）** → 导出活动实测可用（之前直接加 dex 不补 manifest 会 Error type 3！）。产物：`build/fl26_pl_align_tools.apk`（442,215,660B，gamedata sha16=8a3e5afe=gamedata_pl2 ✓，10 个 dex，存档保留）。
**现状**：设备=对齐数据（28 联赛真名）+ 完整存档（pid 全对齐）+ 工具可用（可随时导出/导入）。难度：友谊赛=3、联赛=3（弹窗可调）。
**待用户实测**：联赛改档打一局 + 友谊赛一局，报模式与 AI 表现；若仍无区别→下一步查 difficulty→AIConfig/AIPlayingStyleConfig 的引擎映射段。

---
## 里程碑（2026-10-10 晚）：难度链路深挖 + 首个代码级补丁实验（NOP 强制归零）
**用户实测反馈**：修好存档/数据后，联赛+友谊仍"任何挡位都是 beginner"。
**存档侧复核**：设备 player.dat（9333B）difficulty_selection=false（服务器值）/ CommonDifficulty=3 / friendlyDifficulty=3 —— 读数正确、且**历次调档其实都写入了**（历史值 3/4/3）。→ 问题在**下游**（值没进引擎或被归零）。
**反汇编深挖（libil2cpp.so）**：
- `GenerateAIConfig(CupMatchBase)`（4 个比赛场景 Awake 调用）= AIConfig 工厂；**match_difficult(0x18) = (gate ? matchManager.Difficulty() : 0.0f)**，gate w23=(EasyInt某键<1)&&(miniGameId!=6) —— 值为 0/缺省时**强制 0.0=beginner**；同处 match_duration 也被该键分叉（<1 → 常数 s8）。
- `League.Difficulty()` = `matchDifficulty[GetDifficulty 行][ clamp(archive.WinningStreak/4,-1,1)+1 列]`（表=League+0x78，metadata 常量初始化，5×3）；MasterLeague+new_dynamic_difficulty_rule=1 时走 RegionalLeague 动态难度。
- 引擎侧：配置串含 `"match_difficulty" "{0}"` / `"teammate_difficulty"` / `"difficulty_curve_version"` + 一堆 `ai_*`（libfootball.so=比赛引擎）。
- player.dat 结构（今回合同前段）：16B 头 + `18 01 22 <len>` envelope + UserSetting{f3 ABTest / f5 EasyInt}。
**代码级实验 #1（已装机）**：`libil2cpp.so @0x10E99DC` 将 `fcsel s0,s0,s1,eq`（gate→0.0）**改成 NOP** → match_difficult 永远取 matchManager.Difficulty() 的返回值。产物 `build/fl26_pl_align_tools_p1.apk`（442MB，含对齐数据+工具），install -r 保档，启动测试无崩溃 ✓。
**待用户实测**：Top Player vs Beginner 各一局（联赛+友谊）对比 AI 强度。
- 若有区别 → gate 即元凶 → 正式化该补丁 + 查 gate 键名（候选：EasyInt 缺省键）。
- 若无区别 → 实验 #2：把该处 patch 为 `fmov s0,#3.0`（或更大）测引擎是否响应 match_difficult。
**关键坐标**：patch 文件偏移 0x10E99DC（原字节 00 0c 21 1e）；store 在 0x10E99E0；blr(Difficulty) 在 0x10E99D0。
