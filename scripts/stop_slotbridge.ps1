$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $projectRoot '.slotbridge-backend.pid'
$runFile = Join-Path $projectRoot 'run.py'

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host 'Локальный backend SlotBridge уже остановлен.' -ForegroundColor Yellow
    exit 0
}

$backendPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
if ($backendPid -notmatch '^\d+$') {
    Write-Host 'Файл процесса повреждён; процесс не остановлен.' -ForegroundColor Red
    exit 1
}

$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $backendPid" -ErrorAction SilentlyContinue
if (-not $processInfo) {
    Remove-Item -LiteralPath $pidFile -Force
    Write-Host 'Локальный backend SlotBridge уже остановлен.' -ForegroundColor Yellow
    exit 0
}

if ($processInfo.CommandLine -notlike "*$runFile*") {
    Write-Host 'PID принадлежит другому приложению; процесс не остановлен.' -ForegroundColor Red
    exit 1
}

Stop-Process -Id ([int]$backendPid)
Wait-Process -Id ([int]$backendPid) -Timeout 10 -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host 'Backend SlotBridge остановлен. PostgreSQL продолжает работать.' -ForegroundColor Green
