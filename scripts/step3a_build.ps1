# step3a_build.ps1 — Step 3A 构建脚本（复用 Step 2 流水线，零资源改动）
# 用途：生成带 side-by-side 包名的可装 APK。本阶段不做数据修改。
$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
$ROOT = "C:\FL26_Mod"
$BT   = "$ROOT\android-sdk\build-tools\36.0.0"
$ADB  = "$ROOT\android-sdk\platform-tools\adb.exe"

Write-Host "[1/4] copy working -> ascii staging"
Copy-Item "$ROOT\working\base.apk" "$ROOT\working_ascii\base_poc.apk" -Force

Write-Host "[2/4] manifest package rename + provider uniquify"
python "$ROOT\scripts\axml_provider_scan.py"
python "$ROOT\scripts\arsc_pkg_rename.py"

Write-Host "[3/4] align + sign"
& "$BT\zipalign.exe" -p -f 4 "$ROOT\build\base_renamed2.apk" "$ROOT\build\base_renamed2_aligned.apk"
& "$BT\apksigner.bat" sign --ks "$ROOT\build\fl26_test.keystore" --ks-pass pass:fl26modtest --key-pass pass:fl26modtest --out "$ROOT\dist\fl26_custom_player_step3a.apk" "$ROOT\build\base_renamed2_aligned.apk"
& "$BT\apksigner.bat" verify "$ROOT\dist\fl26_custom_player_step3a.apk" | Select-Object -First 1

Write-Host "[4/4] done -> dist\fl26_custom_player_step3a.apk"
