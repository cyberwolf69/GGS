$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
foreach ($mode in @('paper','live')) {
    foreach ($name in @('telegram','dashboard','engine')) {
        $pidFile = Join-Path $Root "runtime\$mode\$name.pid"
        if (Test-Path $pidFile) {
            $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue
            if ($pidValue) { Stop-Process -Id ([int]$pidValue) -Force -ErrorAction SilentlyContinue }
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host 'GGS stopped.'
