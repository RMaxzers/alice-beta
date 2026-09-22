<#
.SYNOPSIS  Consistent backup (SQLite online backup + Qdrant snapshot + files + sha256 manifest) into backups\. Keeps newest 7.
#>
. "$PSScriptRoot\_common.ps1"
& (Join-Path $Root '.venv\Scripts\python.exe') -m scripts.backup backup
exit $LASTEXITCODE
