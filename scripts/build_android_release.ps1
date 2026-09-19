param([string]$VersionName = '1.1.0', [int]$VersionCode = 4)
$ErrorActionPreference = 'Stop'
$flutterRoot = 'D:\SlotBridgeAndroidTooling\flutter'
$dart = Join-Path $flutterRoot 'bin\cache\dart-sdk\bin\dart.exe'
$packages = '--packages=' + (Join-Path $flutterRoot 'packages\flutter_tools\.dart_tool\package_config.json')
$snapshot = Join-Path $flutterRoot 'bin\cache\flutter_tools.snapshot'
$env:GRADLE_USER_HOME = 'D:\SlotBridgeAndroidTooling\gradle-cache'
$env:PUB_CACHE = 'D:\SlotBridgeAndroidTooling\pub-cache'
$env:JAVA_HOME = 'D:\SlotBridgeAndroidTooling\jdk\jdk-17.0.20.1+1'
$env:ANDROID_HOME = 'D:\SlotBridgeAndroidTooling\android-sdk'
$env:FLUTTER_STORAGE_BASE_URL = 'file:///C:/Users/User/AppData/Local/Temp/slotbridge-flutter-verified-mirror'
Push-Location (Join-Path $PSScriptRoot '..\mobile')
try { & $dart $packages $snapshot build apk --release --no-pub --build-name=$VersionName --build-number=$VersionCode --dart-define=SLOTBRIDGE_ENVIRONMENT=production --dart-define=SLOTBRIDGE_API_BASE_URL=https://slotbridge-api.onrender.com }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw 'Flutter release build failed.' }
$source = Join-Path $PSScriptRoot '..\mobile\build\app\outputs\flutter-apk\app-release.apk'
$destinationDirectory = Join-Path $PSScriptRoot '..\artifacts\android'
New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
$destination = Join-Path $destinationDirectory "SlotBridge-$VersionName-$VersionCode-production.apk"
Copy-Item -LiteralPath $source -Destination $destination -Force
$sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "APK=$([IO.Path]::GetFullPath($destination))"
Write-Output "SHA256=$sha256"
Write-Output "Prepared only. Public release requires explicit approval."
