$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Get-GgsPython {
    $candidates = @(
        @{Cmd='py'; Args=@('-3.13')},
        @{Cmd='py'; Args=@('-3.12')},
        @{Cmd='py'; Args=@('-3.11')},
        @{Cmd='python'; Args=@()},
        @{Cmd='python3'; Args=@()}
    )
    foreach ($c in $candidates) {
        if (Get-Command $c.Cmd -ErrorAction SilentlyContinue) {
            try {
                $ver = & $c.Cmd @($c.Args) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $parts = $ver.Trim().Split('.')
                    if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11)) {
                        return $c
                    }
                }
            } catch {}
        }
    }
    throw 'Python 3.11+ is required.'
}

if (-not (Test-Path '.env') -and (Test-Path '.env.example')) {
    Copy-Item '.env.example' '.env'
    Write-Host '[GGS] Creating .env from .env.example'
}

# Load simple KEY=VALUE pairs from .env into process environment.
if (Test-Path '.env') {
    Get-Content '.env' | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $kv = $line.Split('=', 2)
            [Environment]::SetEnvironmentVariable($kv[0].Trim(), $kv[1].Trim(), 'Process')
        }
    }
}

$env:GGS_MODE = 'PAPER'
$env:GGS_ROOT = $Root
if (-not $env:GGS_PORT) { $env:GGS_PORT = '6969' }

$py = Get-GgsPython
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host "[GGS] Creating .venv..."
    & $py.Cmd @($py.Args) -m venv .venv
}

$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'
& $PythonExe -m pip install -q --upgrade pip
& $PythonExe -m pip install -q -r requirements.txt

$CertPath = (& $PythonExe -m certifi).Trim()
$env:SSL_CERT_FILE = $CertPath
$env:REQUESTS_CA_BUNDLE = $CertPath

$Runtime = Join-Path $Root 'runtime\paper'
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

# Stop any previous GGS processes recorded in PID files.
foreach ($name in @('telegram','dashboard','engine')) {
    $pidFile = Join-Path $Runtime "$name.pid"
    if (Test-Path $pidFile) {
        $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($oldPid) { Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

# Free GGS dashboard port if an older listener is still attached.
try {
    Get-NetTCPConnection -LocalPort ([int]$env:GGS_PORT) -State Listen -ErrorAction Stop |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
} catch {}

function Start-GgsProcess([string]$Name, [string[]]$Arguments) {
    $out = Join-Path $Runtime "$Name.log"
    $err = Join-Path $Runtime "$Name.err.log"
    $p = Start-Process -FilePath $PythonExe -ArgumentList $Arguments -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
    Set-Content -Path (Join-Path $Runtime "$Name.pid") -Value $p.Id
    return $p.Id
}

$enginePid = Start-GgsProcess 'engine' @('-m','ggs.runtime')
$dashboardPid = Start-GgsProcess 'dashboard' @('-m','uvicorn','ggs.app:app','--host','127.0.0.1','--port',$env:GGS_PORT)

$telegramStatus = 'OFF (configure .env)'
if ($env:TELEGRAM_BOT_TOKEN -and $env:TELEGRAM_OWNER_ID) {
    $telegramPid = Start-GgsProcess 'telegram' @('-m','ggs.telegram.bot')
    $telegramStatus = "ON (pid $telegramPid)"
}

Start-Sleep -Seconds 1
Write-Host ''
Write-Host 'GGS — Ganteng-Ganteng Signature'
Write-Host 'Runtime: PAPER / LIVE READ-ONLY / SHADOW / LIVE via Telegram /mode'
Write-Host "Dashboard: http://127.0.0.1:$($env:GGS_PORT)"
Write-Host "Engine PID: $enginePid"
Write-Host "Dashboard PID: $dashboardPid"
Write-Host "Telegram: $telegramStatus"
