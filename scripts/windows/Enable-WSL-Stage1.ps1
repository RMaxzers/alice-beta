<#
.SYNOPSIS  Phase 2 / stage 1 (run as ADMINISTRATOR): enable the WSL platform. Does NOT reboot.
           Creates a restore point, records the boot configuration, runs `wsl --install --no-distribution`.
           The hypervisor becomes active only after YOU reboot. Then run Check-PostReboot.ps1.
.NOTES     Rollback instructions: docs/PHASE2-WSL-DOCKER.md ("Rollback").
#>
. "$PSScriptRoot\_common.ps1"
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Ejecuta este script en PowerShell "Ejecutar como administrador".'
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$bk = Join-Path $Root "backups\phase2-$stamp"
New-Item -ItemType Directory -Force $bk | Out-Null

Write-Host '==> Pre-flight' -ForegroundColor Cyan
$gpu = & nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>$null
if ($LASTEXITCODE -ne 0) { throw 'nvidia-smi falla ANTES del cambio: no continuar (estado base no sano).' }
$resets = @(Get-WinEvent -FilterHashtable @{LogName='System'; Id=41; StartTime=(Get-Date).AddDays(-3)} -ErrorAction SilentlyContinue).Count
Write-Host "  GPU: $gpu"
Write-Host "  Kernel-Power 41 en los últimos 3 días: $resets"
if ($resets -gt 0) { Write-Warning 'Hubo reinicios inesperados recientes. Recomendado: posponer hasta tener 3 días sin resets.'; if ((Read-Host 'Continuar igualmente? (si/no)') -ne 'si') { exit 1 } }

Write-Host '==> Recording current boot/feature state (read-only)' -ForegroundColor Cyan
bcdedit /enum '{current}' | Out-File (Join-Path $bk 'bcdedit-current.txt') -Encoding utf8
Get-WindowsOptionalFeature -Online | Where-Object FeatureName -match 'VirtualMachinePlatform|Microsoft-Windows-Subsystem-Linux|Hyper-V|HypervisorPlatform|Containers' |
  Select-Object FeatureName, State | Format-Table -AutoSize | Out-File (Join-Path $bk 'features-before.txt') -Encoding utf8
Get-PnpDevice -Class Display | Select-Object FriendlyName, Status, Problem, InstanceId | Out-File (Join-Path $bk 'display-before.txt') -Encoding utf8
Write-Host "  saved to $bk"

Write-Host '==> Restore point' -ForegroundColor Cyan
try {
  Checkpoint-Computer -Description 'Pre-WSL2-Alice' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop
  Write-Host '  created: Pre-WSL2-Alice'
} catch {
  Write-Warning "No se pudo crear el punto de restauración ($($_.Exception.Message)). Windows limita 1 cada 24 h; el ancla anterior 'PreNVIDIA-Retry-Stable-BasicDisplay' y los existentes siguen disponibles."
  if ((Read-Host 'Continuar sin punto nuevo? (si/no)') -ne 'si') { exit 1 }
}

Write-Host '==> Enabling WSL platform (wsl --install --no-distribution)' -ForegroundColor Cyan
& wsl.exe --install --no-distribution
if ($LASTEXITCODE -ne 0) { throw "wsl --install falló (código $LASTEXITCODE)" }

Write-Host @"

LISTO. Aún NO se reinició.
1. Guarda tu trabajo y reinicia cuando tú decidas.
2. Tras el login ejecuta:  powershell -ExecutionPolicy Bypass -File $Root\scripts\windows\Check-PostReboot.ps1
3. Si Windows no arranca: ver 'Rollback' en docs\PHASE2-WSL-DOCKER.md (WinRE -> bcdedit hypervisorlaunchtype off).
"@ -ForegroundColor Green
