$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'RASDAD: http://127.0.0.1:8000'
Write-Host 'Keep this window open while using the website.'
python server.py
