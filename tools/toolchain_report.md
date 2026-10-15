# Gate 2B — Android Toolchain Report

**Date**: 2026-08-31 10:40 +08:00

| 工具 | 版本 | 路径 | 可执行 |
|---|---|---|---|
| Java JDK (Microsoft OpenJDK 21 LTS) | 21.0.12.1 | `C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot` | ✅ `java -version` OK |
| JAVA_HOME | — | 已写入 User 环境变量 | ✅ |
| Android SDK cmdline-tools | 11076708 | `C:\FL26_Mod\android-sdk\cmdline-tools\latest` | ✅ |
| adb | 1.0.41 (37.0.1-15733141) | `C:\FL26_Mod\android-sdk\platform-tools\adb.exe` | ✅ |
| apksigner | 0.9 | `C:\FL26_Mod\android-sdk\build-tools\36.0.0\apksigner.bat` | ✅ |
| zipalign | 36.0.0 | `C:\FL26_Mod\android-sdk\build-tools\36.0.0\zipalign.exe` | ✅ |

安装来源：winget (Microsoft.OpenJDK.21) + dl.google.com 官方 zip（直连可用，无代理需求）。
未安装重复组件。无 Android Studio 完整 IDE（不需要）。

**设备状态**: `adb devices` = 空（守护进程已启动，无设备连接）→ Gate 2C 的安装/启动验证需要连接真机或模拟器。

**Gate 2B: PASS**
