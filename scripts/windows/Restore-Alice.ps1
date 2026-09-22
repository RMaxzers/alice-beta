<#
.SYNOPSIS  Verify and restore a backup into an EXPLICIT new folder (never over live data).
           Qdrant is verified by restoring the snapshot into a temporary collection that is then dropped.
.EXAMPLE   .\Restore-Alice.ps1 -Backup ..\..\backups\alice-20260922-150000 -Destination C:\Temp\alice-restore-test
#>
param([Parameter(Mandatory)][string]$Backup, [Parameter(Mandatory)][string]$Destination)
. "$PSScriptRoot\_common.ps1"
Push-Location $Root
& (Join-Path $Root '.venv\Scripts\python.exe') -m scripts.backup restore $Backup $Destination
$rc = $LASTEXITCODE; Pop-Location; exit $rc
