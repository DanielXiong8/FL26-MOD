# PHASE 14A — Browser Face Builder V1 Report

日期：2026-09-08
状态：**代码全部就绪；BUILD 管线冒烟通过；浏览器全流程 E2E 待执行**

---

## A. SaveExport / SaveImport 是否打通

**PASS（用户真机确认）**。链路：`SaveExportActivity → PC protobuf 编辑 → SaveImportActivity → install -r 装回游戏 → 游戏内生效`。验证内容：从中国队名单移除探针 P13B_P07（33→32 人），用户确认"对，消失了"。编辑器：`D:\FL26_Mod\work\save_pipeline\phase14a\save_editor.py`（字节保真自测通过）。

## B. 是否取消"必须清装重装"

**部分取消，如实记录 `SAVE_IMPORT_LIMITATION`**：
- ✅ 名单归属/换队/移除：免重装（Save Import 直达）
- ❌ 新球员创建：必须 BUILD APK（player_blob 只是状态摘要 f1=pid/f2=状态/f5=队/f10=评分，不含名字/属性/外观——已实测）

产品流定型：**BUILD PLAYER**（APK，每批一次安装）+ **IMPORT TO DEVICE**（免重装名单操作）。

## C. Web 页面是否完成

**代码完成**：`D:\FL26_Mod\tools\FL26_FaceBuilderWeb\`（FastAPI 后端 + 原生 HTML/CSS/JS）。八步流程 UI（上传→候选→选脸→微调→信息→球队→生成→安装/导入）+ Roster Manager + Advanced 面板。服务器冒烟通过（catalog API 1853 队/217 国籍/19 Reference/10 发色/22 胡型）。

## D. 三张照片是否支持

**代码完成**：拖拽/多选上传、缩略图、PRIMARY 标记（第一张主照片进候选管线）。E2E 待跑。

## E. Reference Player 是否完成

**完成**：19 名真实中国队球员（Wu L./Le L./Yang J. 等，来自 `phase13b/analysis/reference_players_chn.json`）。

## F. 发色/胡子/眉型是否完成

**完成**：发色 10 色（b5，3D 粉发真机确认）、胡型 22 种（b6，P11 髭确认）、眉型 7 种（b8）。b14/b3 = Follow Reference Player（不伪造滑杆），Eyes = Coming in V2。

## G. 人物信息是否完成

**代码完成**：Name、Position（FW=设备验证档/GK=Yang J. 真档/MF·DF=构造档标注实验）、Preferred Foot=NOT EXPOSED（字段未定位，不猜）、Nationality（217 国真实表）、Jersey 1–99+队内查重、17 Attributes（三预设+自定义）。全走真实字段。

## H. BUILD PLAYER 是否完成

**冒烟 PASS**：独立联调一次成功——25/33 队容检查、41 号球衣查重、pid 175924 分配、PA 字节覆盖（发色5/胡型8/眉型4）、gamedata 三表注入、APK 重打包、签名+验证 OK，产物 442MB `player.apk`。

## I. INSTALL 是否完成

**代码完成**（BUILD/SIGN/VERIFY 三 PASS 才允许 INSTALL，显示 package/size/SHA256）。待 E2E。

## J. IMPORT TO DEVICE 是否完成

**代码完成**（Roster Manager：Export → 选球员 → Import，明确标注"新球员需 BUILD PLAYER"）。机制本身 SAVE_ROUNDTRIP 已真机 PASS。

## K. Ma Jiantao 完整 E2E 是否 PASS

**待执行**——这是 V1 的最终 gate：浏览器上传马健涛照片 → 全流程 → INSTALL → League 比赛。

## L. Roster Manager 是否 PASS

机制 PASS（SAVE_ROUNDTRIP）；Web 按钮 E2E 待跑。

## M. BROWSER_FACE_BUILDER_V1 状态

**IN_PROGRESS** —— 代码全就绪、管线冒烟绿、剩浏览器全流程 E2E（需要设备 + 马健涛照片跑一遍）+ 收尾（V1 只做已验证选项的原则全程未破坏）。

## 阶段 Gate 表（详见 `D:\FL26_Mod\recon\reports\PHASE14A_WEB_STATUS.json`）

| Gate | 状态 |
|---|---|
| SAVE_EXPORT_READY / SAVE_ROUNDTRIP_READY | **GREEN**（用户确认） |
| WEB_INPUT/CANDIDATE/FACE/PLAYER_CONFIG/BUILD/INSTALL | GREEN_CODE（E2E 待跑） |
| NEW_PLAYER_SAVE_READY | BLOCKED_BY_DESIGN（LIMITATION 如实记录） |
| WEB_E2E_READY | PENDING |

## 启动方式

```
cd D:\FL26_Mod\tools\FL26_FaceBuilderWeb
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
浏览器: http://127.0.0.1:8765
```
