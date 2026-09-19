$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = 'utf-8'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envFile = Join-Path $projectRoot '.env'
$requirementsFile = Join-Path $projectRoot 'requirements.txt'
$venvDirectory = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venvDirectory 'Scripts\python.exe'
$requirementsMarker = Join-Path $venvDirectory '.slotbridge-requirements.sha256'
$pidFile = Join-Path $projectRoot '.slotbridge-backend.pid'
$runFile = Join-Path $projectRoot 'run.py'
$dataDirectory = Join-Path $projectRoot 'data'

function Write-Step([string]$Message) {
    Write-Host $Message -ForegroundColor Cyan
}

function Stop-WithMessage([string]$Message) {
    Write-Host "ОШИБКА: $Message" -ForegroundColor Red
    exit 1
}

function Get-PrivateLanAddress {
    $defaultRoutes = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Sort-Object RouteMetric, InterfaceMetric
    foreach ($route in $defaultRoutes) {
        $addresses = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
        foreach ($address in $addresses) {
            $ip = $address.IPAddress
            if ($ip -match '^10\.' -or
                $ip -match '^192\.168\.' -or
                $ip -match '^172\.(1[6-9]|2[0-9]|3[01])\.') {
                return $ip
            }
        }
    }
    return $null
}

function Find-PostgresTool([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $roots = @('C:\Program Files\PostgreSQL', 'D:\PostgreSQL')
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $candidate = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "bin\$Name.exe" } |
            Where-Object { Test-Path -LiteralPath $_ } |
            Select-Object -First 1
        if ($candidate) { return $candidate }
    }
    return $null
}

Set-Location $projectRoot
Write-Host ''
Write-Host 'SlotBridge' -ForegroundColor Green
Write-Host '----------' -ForegroundColor Green

if (-not (Test-Path -LiteralPath $envFile)) {
    Stop-WithMessage 'Не найден .env. Скопируйте .env.example в .env и задайте локальные секреты.'
}

$pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $pythonLauncher -and -not $pythonCommand) {
    Stop-WithMessage 'Python не найден. Установите Python 3.12 и повторите запуск.'
}
Write-Host 'Python: OK' -ForegroundColor Green

$pgIsReady = Find-PostgresTool 'pg_isready'
if (-not $pgIsReady) {
    Stop-WithMessage 'Не найден pg_isready.exe в установленном PostgreSQL.'
}
& $pgIsReady -h 127.0.0.1 -p 5432 -q
if ($LASTEXITCODE -ne 0) {
    $postgresService = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $postgresService) {
        Stop-WithMessage 'Служба PostgreSQL Windows не найдена. Выполните раздел Local Windows setup в README.md.'
    }
    Write-Step 'Запускаем службу PostgreSQL Windows...'
    try {
        Start-Service -Name $postgresService.Name
        $postgresService.WaitForStatus('Running', [TimeSpan]::FromSeconds(20))
    } catch {
        Stop-WithMessage "Не удалось запустить службу $($postgresService.Name). Запустите этот файл от имени администратора один раз."
    }
    & $pgIsReady -h 127.0.0.1 -p 5432 -q
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage 'PostgreSQL не отвечает на 127.0.0.1:5432. Проверьте службу и конфликт с Docker.'
    }
}
Write-Host 'PostgreSQL: OK' -ForegroundColor Green

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step 'Создаём изолированное Python-окружение...'
    if ($pythonLauncher) {
        & $pythonLauncher.Source -3.12 -m venv $venvDirectory
    } else {
        & $pythonCommand.Source -m venv $venvDirectory
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        Stop-WithMessage 'Не удалось создать .venv.'
    }
}

$requirementsHash = (Get-FileHash -LiteralPath $requirementsFile -Algorithm SHA256).Hash
$installedHash = if (Test-Path -LiteralPath $requirementsMarker) {
    (Get-Content -LiteralPath $requirementsMarker -Raw).Trim()
} else { '' }
if ($requirementsHash -ne $installedHash) {
    Write-Step 'Устанавливаем необходимые Python-зависимости...'
    & $venvPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Не удалось установить Python-зависимости.' }
    [System.IO.File]::WriteAllText($requirementsMarker, $requirementsHash)
}

Write-Step 'Проверяем подключение к базе slotbridge...'
& $venvPython -c "from sqlalchemy import text; from app.database import engine; assert engine.dialect.name == 'postgresql'; connection = engine.connect(); assert connection.scalar(text('SELECT current_database()')) == 'slotbridge'; connection.close()"
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage 'Не удалось подключиться к базе slotbridge. Проверьте DATABASE_URL и пароль в .env.'
}
Write-Host 'Database: slotbridge (PostgreSQL) — OK' -ForegroundColor Green

Write-Step 'Применяем миграции...'
& $venvPython -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Alembic migration завершилась с ошибкой.' }
Write-Host 'Migrations: OK' -ForegroundColor Green

Write-Step 'Проверяем демонстрационные данные...'
& $venvPython (Join-Path $projectRoot 'scripts\seed_domain.py')
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Подготовка demo-данных завершилась с ошибкой.' }
Write-Host 'Demo data: OK' -ForegroundColor Green

try {
    $existing = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/health/ready' -TimeoutSec 2
    if ($existing.StatusCode -eq 200) {
        Stop-WithMessage 'Порт 8000 уже занят работающим backend. Сначала используйте stop_slotbridge.bat.'
    }
} catch {
    if ($_.Exception.Response) {
        Stop-WithMessage 'Порт 8000 занят другим приложением.'
    }
}

$quotedRunFile = '"' + $runFile + '"'
New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
$stdoutLog = Join-Path $dataDirectory 'slotbridge-backend.out.log'
$stderrLog = Join-Path $dataDirectory 'slotbridge-backend.error.log'
$backend = Start-Process -FilePath $venvPython -ArgumentList $quotedRunFile -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
[System.IO.File]::WriteAllText($pidFile, [string]$backend.Id)

$ready = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    if ($backend.HasExited) { break }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/health/ready' -TimeoutSec 1
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch { }
    Start-Sleep -Milliseconds 250
}

if (-not $ready) {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $stderrLog) {
        Get-Content -LiteralPath $stderrLog -Tail 20 -ErrorAction SilentlyContinue
    }
    Stop-WithMessage 'Backend не прошёл проверку готовности.'
}

$lanIp = Get-PrivateLanAddress
Write-Host 'Backend: http://localhost:8000' -ForegroundColor Green
if ($lanIp) {
    Write-Host "Phone backend: http://${lanIp}:8000" -ForegroundColor Green
} else {
    Write-Host 'Phone backend: LAN IPv4 не определён; выполните ipconfig.' -ForegroundColor Yellow
}
Write-Host ''
Write-Host 'Backend работает. Не закрывайте это окно во время демонстрации.' -ForegroundColor Yellow
Write-Host 'Для остановки дважды нажмите stop_slotbridge.bat.' -ForegroundColor Yellow
Write-Host "Логи: $stdoutLog и $stderrLog" -ForegroundColor DarkGray

try {
    $backend.WaitForExit()
} finally {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
Write-Host 'Backend SlotBridge остановлен.'
exit 0
