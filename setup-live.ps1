$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv/Scripts/python.exe")) {
  Write-Host "[GGS] Run .\\start.ps1 once first to create .venv."
  exit 1
}
& ".venv/Scripts/python.exe" -m ggs.live.setup
