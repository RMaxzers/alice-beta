<#
.SYNOPSIS  Runs unit + security tests, integration tests (if Alice is up) and the router evaluation.
#>
param([switch]$SkipRouterEval)
. "$PSScriptRoot\_common.ps1"
Push-Location $Root
& (Join-Path $Root '.venv\Scripts\python.exe') -m pytest -q -p no:cacheprovider
$rc = $LASTEXITCODE
if (-not $SkipRouterEval) { & (Join-Path $Root '.venv\Scripts\python.exe') -m tests.routing.eval_router }
Pop-Location
exit $rc
