$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
foreach ($name in @('engine','dashboard','telegram')) {
    $pidFile = Join-Path $Root "runtime\paper\$name.pid"
    if (-not (Test-Path $pidFile)) {
        Write-Host "$name`: NOT STARTED"
        continue
    }
    $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue
    $proc = $null
    if ($pidValue) { $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue }
    if ($proc) { Write-Host "$name`: RUNNING (pid $pidValue)" }
    else { Write-Host "$name`: STOPPED" }
}
