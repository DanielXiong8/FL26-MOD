# FL26 Face Builder Web — V1

浏览器版人物生成器（Phase 14A）。Orchestration only：所有游戏侧操作调用已真机验证的管线，不在 Web 内重写任何注入/存档逻辑。

## 启动

```bash
cd D:\FL26_Mod\tools\FL26_FaceBuilderWeb
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

浏览器打开 http://127.0.0.1:8765

## 用户流程

1. **上传照片**（1–3 张，第一张为主照片）
2. **生成候选**（调用 `face_benchmark/scripts/generate_candidates.py`，PASS 可选/REJECT 灰显）
3. **选择候选**（SELECT）
4. **外观微调**：
   - Face / Hair / Face Shape：`Follow Reference Player`（19 名真实中国队球员）
   - Hair Color：10 色（b5，真机验证）
   - Beard：22 种（b6，真机验证 P11 髭）
   - Eyebrow：7 种（b8）
   - Eyes：Coming in V2
5. **人物信息**：Name / Position（GK·DF·MF·FW 属性模板）/ Nationality（真实国籍表 217 国）/ Jersey（1–99，队内查重）/ 17 Attributes（预设+自定义）
6. **球队**：真实 Teams 表（1853 队），实时显示 `roster X / 33`，**达上限禁止 BUILD**（43 人死局实锤约束）
7. **BUILD PLAYER**：PID 分配 → gamedata 注入（Player/ClubPlayer/PA 字节覆盖）→ TEXTURE-ONLY 脸纹理注入 → zipalign/sign/verify
8. **INSTALL TO DEVICE**（adb）/ **Roster Manager**（SaveExport → save_editor → SaveImport 免重装调名单）

## 架构（单一事实源）

| 能力 | 实现（不复制） |
|---|---|
| 候选生成 | `face_benchmark/scripts/generate_candidates.py`（subprocess） |
| 球员注入 | `backend/inject_player_v1.py`（= Phase13B 设备验证公式参数化） |
| 脸纹理注入 | `backend/texture_inject.py`（TEXTURE-ONLY，无 MICA 红线） |
| 存档编辑 | `work/save_pipeline/phase14a/save_editor.py` |
| 外观语义 | `backend/appearance_state.py`（Phase13B 字节语义） |
| 球队/国籍 | `backend/data_catalog.py`（读真实 gamedata 表，缓存 catalog_cache.json） |

## 已知边界（V1 如实标注）

- `SAVE_IMPORT_LIMITATION`：存档导入只能调动/移除 **gamedata 已有**球员（player_blob=状态摘要），新球员必须 BUILD APK
- b14/b3/Eyes/Preferred Foot：未开放（无滑杆伪造）
- 3D Preview：V1 为手动 "Render Preview"（Phase13BRender batch），目标 <5s 常驻渲染在 V2
- 位置模板：FW 为设备验证档（uniform 81-97→门将的教训），GK=Yang J. 真档，MF/DF 为构造档（实验标注）
- 共享纹理：照片脸写入 face_eastAsia_new1 后，所有 b1=14 球员共享（游戏架构固有）
