# PC_AVATAR_PREVIEWER_SETUP.md

> 安装 Unity 后按本文件操作。全文路径均为绝对路径，可直接复制。

## 1. 安装 Unity

- Unity Hub → Installs → Install Editor → **2020.3.49f1**（Archive 里可找到；如 Hub 中无此版本，用直接下载链接：
  `https://download.unity3d.com/download_unity/18249dd5551b/Windows64EditorInstaller/UnitySetup64-2020.3.49f1.exe`
  （revision `18249dd5551b` 来自 Unity 官方 releases API 实查；2026-09-05 前记录的 `a8928a80ccc7` 为错误 hash，已实测 404））
- 模块只需 **Windows Build Support (IL2CPP 可不装)**，不要装 Android/URP/HDRP。

## 2. 打开工程

- Unity Hub → Open → 选择目录：`D:\FL26_Mod\tools\FL26_AvatarPreviewer`
  （2026-09-05 起 PROJECT_ROOT 为 `D:\FL26_Mod`；旧 `C:\FL26_Mod` 已弃用）
- 版本识别依据 `ProjectSettings\ProjectVersion.txt`（内容为 2020.3.49f1）。
- 首次打开 Unity 会自动生成缺失的 ProjectSettings/Library（本仓库刻意不预置这些文件）。
- 若项目再次整体搬家（改盘符/目录），无需改脚本：设置环境变量 `FL26_PROJECT_ROOT` 指向新根目录即可；
  否则脚本会从本工程目录向上自动寻找包含 `build\avatar.unity3d` 的祖先目录作为 PROJECT_ROOT。

## 3. 运行（无需打开任何场景）

1. 任意打开或新建一个空场景（File → New Scene → Empty）。
2. 直接按 **Play** ▶。
3. `PreviewerBootstrap` 通过 `RuntimeInitializeOnLoadMethod` 自动启动：
   - 自动按搜索顺序加载 `avatar.unity3d`（相对 PROJECT_ROOT = `D:\FL26_Mod` 解析，只读）：
     1. `<PROJECT_ROOT>\build\avatar.unity3d`（原始 FL26 资产，只读，绝不修改）
     2. `<Unity工程>\extracted\avatar.unity3d`（若存在本地副本）
   - 自动枚举全部 Mesh/Material/Texture2D/Shader/GameObject →
     `viewer_outputs 之外` 写入 `runs\preview\asset_enumeration.txt`
   - 自动加载 `face_EastAsia_new1`，并把该 Avatar 依赖（Mesh/SMR/Material/Shader/Texture/槽位/bones）写入
     `runs\preview\deps_face_EastAsia_new1.txt`
   - 自动输出首张截图 `runs\preview\auto_face_EastAsia_new1_front.png`
   - 加载状态写入 `runs\preview\load_state.txt`

## 4. 操作

| 输入 | 功能 |
|------|------|
| 鼠标左键拖动 | 旋转 |
| 滚轮 | 缩放 |
| `1` / `2` / `3` / `4` | 正面 / 左45° / 右45° / 侧面 |
| `N` | 切换下一个脸（new1→…→new6 循环） |
| `C` | 加载候选纹理（默认 `<PROJECT_ROOT>\face_benchmark\runs\test01\candidates\c4\baked.png`，即 `D:\FL26_Mod\face_benchmark\runs\test01\candidates\c4\baked.png`）并自动截图 |
| `P` | 手动截图 → `runs\preview\manual_<avatar>_view.png` |
| `R` | 复位视角 |
| `Esc` | 退出 |

## 5. 选择 Avatar / 加载 c4 baked texture

- 换脸：连按 `N` 循环 `face_EastAsia_new1..new6`（脚本内 `faceObjectNames` 可改）。
- 候选纹理：按 `C`；换路径改脚本内 `candidateTextureCandidates`。
- 观察目标：如需看 **Wu L. / Wei / Liu D. 的真实网格**，先在 `runs\preview\asset_enumeration.txt`
  里确认他们的 head/face GameObject 名称，再改 `faceObjectNames` 数组重新 Play。

## 6. 输出四角度截图

按顺序按 `1`→`P`、`2`→`P`、`3`→`P`、`4`→`P`（文件名含时间戳不覆盖；
如需固定命名 `viewer_front/45L/45R/side.png`，可在控制台日志中改 `Screenshot()` 调用）。
输出目录：`D:\FL26_Mod\tools\FL26_AvatarPreviewer\runs\preview\`

## 7. 验证顺序（对应 Gate 9A-9G）

1. Play 启动无报错 → **9A**
2. `load_state.txt` 中 `bundleLoaded=True` → **9B**（真实 Mesh 显示，见 Game 视图）
3. Game 视图看到贴图（非纯白/纯灰）→ **9C**
4. `deps_*.txt` 中 shader 非 `Hidden/InternalErrorShader` 且无需 fallback → **9D 原生 Shader**
   （若出现 fallback 警告 = SHADER_PC_INCOMPATIBLE，进入 fallback shader 重建流程）
5. 依次 `N` 查看 new1-new6，new2-4 纹理不再是碎块 → **9E**
6. 按 `C` 加载 c4 → **9F**
7. `runs\preview\*.png` 与 Android 真机截图逐项对比（geometry/texture/shader/light/camera）→ **9G**

## 8. 红线

- 原始 `avatar.unity3d` / `base*.apk` 一律只读；Viewer 不写回任何原始资产。
- 本工程不使用 URP/HDRP；只用 Built-in。
