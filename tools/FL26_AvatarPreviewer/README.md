# FL26_AvatarPreviewer - PC Avatar Viewer

# FL26 Avatar Previewer

基于 Unity 2020.3.49f1 的 PC 实时头像预览器。

## 前置条件

- Unity 2020.3.49f1
- FL26 PROJECT_ROOT（当前为 `D:\FL26_Mod`，可用环境变量 `FL26_PROJECT_ROOT` 覆盖）

## 目录结构

```
FL26_AvatarPreviewer/
├── Assets/
│   └── Scripts/
│       └── Runtime/           # 运行时脚本（单文件入口）
│           └── PreviewerBootstrap.cs   # RuntimeInitializeOnLoadMethod 自动启动，无需场景资产
├── extracted/                 # 从 avatar.unity3d 提取的资产
│   ├── meshes/                # 网格
│   ├── textures/              # 纹理
│   ├── materials/             # 材质
│   ├── shaders/               # 着色器
│   ├── gameobjects/           # 游戏对象
│   └── dependency_map.json    # 依赖关系图
├── Packages/
│   └── manifest.json
├── ProjectSettings/
│   └── ProjectVersion.txt     # 2020.3.49f1（ProjectSettings.asset 由 Unity 首开自动生成）
├── runs/preview/              # 运行时输出（截图/enumeration/deps/load_state，Play 后生成）
├── viewer_outputs/            # 早期截图输出（历史）
└── README.md
```

## 使用方式

1. Unity 2020.3.49f1 中打开此项目
2. 新建/打开任意空场景，直接按 Play ▶（`PreviewerBootstrap` 自动启动，无需 Main.unity）
3. 键盘 `1/2/3/4` 切视角，`N` 换脸，`C` 载入候选纹理，`P` 截图
4. 输出见 `runs/preview/`（详细操作见 `PC_AVATAR_PREVIEWER_SETUP.md`）

## 资源提取

用 `extract_avatar_deps.py` 从 `avatar.unity3d` 提取最新资源。

## 候选预览

```
runs/test01/candidates/c4/front.png
runs/test01/candidates/c4/baked.png
```

载入 `baked.png` 即可预览候选 c4 的脸部纹理。