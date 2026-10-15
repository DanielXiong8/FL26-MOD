# build_trackd.ps1 - Step 8 Track D APK build (avatar face texture injection)
$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
$BT = "C:\FL26_Mod\android-sdk\build-tools\36.0.0"

& $BT\zipalign.exe -p -f 4 C:\FL26_Mod\build\base_trackd.apk C:\FL26_Mod\build\base_trackd_aligned.apk
if ($LASTEXITCODE -ne 0) { throw "zipalign failed" }

& $BT\apksigner.bat sign --ks C:\FL26_Mod\build\fl26_test.keystore --ks-pass pass:fl26modtest --key-pass pass:fl26modtest --out C:\FL26_Mod\dist\fl26_trackd_face.apk C:\FL26_Mod\build\base_trackd_aligned.apk
if ($LASTEXITCODE -ne 0) { throw "sign failed" }

& $BT\apksigner.bat verify C:\FL26_Mod\dist\fl26_trackd_face.apk
if ($LASTEXITCODE -ne 0) { throw "verify failed" }
Write-Host "DONE -> C:\FL26_Mod\dist\fl26_trackd_face.apk"
