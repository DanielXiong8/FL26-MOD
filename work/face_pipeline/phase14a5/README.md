# Phase 14A.5 — Geometry Chain (照片→个性化脸型)

目标：让 Web BUILD 产出的球员"像本人"——补上几何链（V1 只有 TEXTURE-ONLY，
所有照片共用中性头网格 = "同一个建模"）。

链路（全部复用已验证组件）：
  1. MICA 单图重建: photo → FLAME mesh(5023v) + identity(300d)   [recon env, mica.tar]
  2. Stage1 对齐:   FL26 模板 ↔ FLAME 68kpt 相似变换              [adapter_stage1.py 参数化]
  3. Stage2c 适配:  ea1 模板 14 锚点 TPS→MICA 形状, falloff       [adapter_stage2c_ea1.py 参数化]
  4. 注入: stage2_ea1.json(700v) + bake → avatar mesh+tex 注入    [phase11_e2e_avatar_inject 模式参数化]

当年临时脚本已删（入口未存档），本目录重建参数化版本，产物每 run 一存。
