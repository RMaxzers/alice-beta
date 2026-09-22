<#
.SYNOPSIS  Return to the native runtime. Stops the Compose project WITHOUT deleting volumes (no `down -v`),
           removes ALICE_RUNTIME/DOCKER_CMD from .env, restarts native services from their untouched data.
           Documents ingested while in docker mode are in SQLite/raw files but their vectors live in the container
           volume: re-ingest them or restore a later backup (see docs/PHASE2-WSL-DOCKER.md).
#>
. "$PSScriptRoot\_common.ps1"
if (Test-DistroRegistered) { Invoke-Compose @('stop') }
$envFile = Join-Path $Root '.env'
Set-Content $envFile (Get-Content $envFile | Where-Object { $_ -notmatch '^(ALICE_RUNTIME|DOCKER_CMD)=' }) -Encoding utf8
$id = Get-OwnPid 'alice-api'; if ($id) { Stop-Process -Id $id; Wait-Process -Id $id -Timeout 15 -ErrorAction SilentlyContinue }
& "$PSScriptRoot\Start-Alice.ps1"
Write-Host 'Runtime nativo restaurado (volúmenes Docker conservados).' -ForegroundColor Green
