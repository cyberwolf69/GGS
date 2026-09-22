$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run .\start.ps1 once first to create .venv.' }
if (Test-Path '.env') {
    Get-Content '.env' | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $kv = $line.Split('=',2); [Environment]::SetEnvironmentVariable($kv[0].Trim(),$kv[1].Trim(),'Process')
        }
    }
}
& '.\.venv\Scripts\python.exe' -m ggs.live.check @args
