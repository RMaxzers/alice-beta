<#
.SYNOPSIS  Phase 2 checkpoint after the reboot (no admin needed). Verifies the machine is healthy with the hypervisor on
           BEFORE installing any distro. Exit code 0 = safe to continue with Install-DockerWSL.ps1.
#>
. "$PSScriptRoot\_common.ps1"
$fail = 0
function Check($name, [bool]$ok, $detail) {
  Write-Host ("[{0}] {1,-38} {2}" -f $(if ($ok) { 'OK  ' } else { 'FAIL' }), $name, $detail) -ForegroundColor $(if ($ok) { 'Green' } else { 'Red' })
  if (-not $ok) { $Script:fail++ }
}
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
Write-Host "Boot: $boot`n"

Check 'Hypervisor activo' ([bool](Get-CimInstance Win32_ComputerSystem).HypervisorPresent) 'HypervisorPresent'
$disp = Get-PnpDevice -Class Display | Where-Object InstanceId -match 'VEN_10DE'
Check 'GPU NVIDIA sin error (no Code 43)' ($disp -and $disp.Status -eq 'OK') "$($disp.FriendlyName) status=$($disp.Status) problem=$($disp.Problem)"
$smi = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null
Check 'nvidia-smi responde' ($LASTEXITCODE -eq 0 -and $smi) "$smi"
$ev = @(Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$boot.AddMinutes(-5)} -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -in 41, 1001, 4101 -or $_.ProviderName -match 'WHEA|nvlddmkm' })
Check 'Sin eventos Kernel-Power/BugCheck/TDR/WHEA' ($ev.Count -eq 0) "$($ev.Count) evento(s) desde el arranque"
$wsl = & wsl.exe --status 2>&1 | Out-String
Check 'WSL instalado' ($LASTEXITCODE -eq 0) (($wsl -replace "`0", '' -split "`n" | Select-Object -First 1).Trim())

# Real GPU inference through native Ollama (the thing most likely to break with the hypervisor)
if (-not (Test-Http 'http://127.0.0.1:11434/api/version')) { Start-Owned 'ollama' $Ollama @('serve') @{ OLLAMA_HOST = '127.0.0.1:11434' }; $null = Wait-Http 'http://127.0.0.1:11434/api/version' 30 }
try {
  $r = Invoke-RestMethod 'http://127.0.0.1:11434/api/generate' -Method Post -TimeoutSec 180 -ContentType 'application/json' `
        -Body (@{ model = 'qwen3:4b-instruct-2507-q4_K_M'; prompt = 'Responde solo: ok'; stream = $false } | ConvertTo-Json)
  $ps = (Invoke-RestMethod 'http://127.0.0.1:11434/api/ps').models | Where-Object name -like 'qwen3*'
  $tps = [math]::Round($r.eval_count / ($r.eval_duration / 1e9), 1)
  Check 'Ollama infiere 100 % en GPU' ($ps -and $ps.size_vram -eq $ps.size) "size_vram=$([math]::Round($ps.size_vram/1GB,1)) GB, $tps tok/s (antes ~100 tok/s)"
} catch { Check 'Ollama infiere en GPU' $false $_.Exception.Message }

Write-Host ''
if ($fail -eq 0) {
  Write-Host 'Máquina sana con hipervisor activo. Recomendado: usar el PC normalmente 1-3 días y volver a correr este script;' -ForegroundColor Green
  Write-Host 'si sigue OK, continuar con Install-DockerWSL.ps1.' -ForegroundColor Green
} else {
  Write-Host "Hay $fail fallo(s). NO continuar. Ver 'Rollback' en docs\PHASE2-WSL-DOCKER.md." -ForegroundColor Red
}
exit $fail
