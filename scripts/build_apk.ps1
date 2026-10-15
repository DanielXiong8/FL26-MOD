# build_apk.ps1 — FL26 Mod one-click build pipeline (extract -> modify -> replace -> align -> sign -> verify)
# Usage: powershell -ExecutionPolicy Bypass -File C:\FL26_Mod\scripts\build_apk.ps1
$ErrorActionPreference = "Stop"
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-21.0.12.101-hotspot"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path

$ROOT   = "C:\FL26_Mod"
$BT     = "$ROOT\android-sdk\build-tools\36.0.0"
$KS     = "$ROOT\build\fl26_test.keystore"
$KSPASS = "fl26modtest"
$ENTRY  = "assets/bundles/gamedata.unity3d"

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$ts] === FL26 build pipeline start ==="

Write-Host "[1/6] extract bundle..."
python "$ROOT\scripts\extract_bundle.py" $ENTRY

Write-Host "[2/6] modify bundle (mutation POC)..."
python "$ROOT\scripts\modify_bundle.py"

Write-Host "[3/6] replace bundle in APK..."
python "$ROOT\scripts\replace_bundle.py"

Write-Host "[4/6] zipalign..."
& "$BT\zipalign.exe" -p -f 4 "$ROOT\build\base_mod.apk" "$ROOT\build\base_mod_aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "zipalign failed" }

Write-Host "[5/6] apksigner sign..."
& "$BT\apksigner.bat" sign --ks $KS --ks-pass "pass:$KSPASS" --key-pass "pass:$KSPASS" `
    --out "$ROOT\dist\fl26_mod_poc.apk" "$ROOT\build\base_mod_aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "apksigner sign failed" }

Write-Host "[6/6] verify..."
& "$BT\apksigner.bat" verify "$ROOT\dist\fl26_mod_poc.apk"
if ($LASTEXITCODE -ne 0) { throw "verify failed" }

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$ts] === DONE -> $ROOT\dist\fl26_mod_poc.apk ==="
