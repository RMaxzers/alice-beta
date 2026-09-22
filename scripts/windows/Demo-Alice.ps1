<#
.SYNOPSIS  Seeds synthetic demo data (idempotent) and rehearses the full demo against the running Alice, writing docs/DEMO-RUN.md.
#>
. "$PSScriptRoot\_common.ps1"
Push-Location $Root
$py = Join-Path $Root '.venv\Scripts\python.exe'
& $py -m scripts.make_samples | Out-Null
& $py -m scripts.demo
$rc = $LASTEXITCODE; Pop-Location; exit $rc
