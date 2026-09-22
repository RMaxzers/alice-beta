<#
.SYNOPSIS  Phase 2 / stage 3: move Qdrant, Prometheus and Grafana from native processes to the Compose project.
           Backup first; native data dirs are left untouched (instant rollback with Rollback-Docker.ps1).
           Prometheus history starts empty in the container (native TSDB kept on disk for rollback).
#>
. "$PSScriptRoot\_common.ps1"
function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
if (-not (Test-DistroRegistered)) { throw "Distro $Distro no existe: ejecuta Install-DockerWSL.ps1" }
if ((Get-Runtime) -eq 'docker') { Write-Host 'ALICE_RUNTIME ya es docker.'; exit 0 }
$py = Join-Path $Root '.venv\Scripts\python.exe'

Step 'Backup (SQLite + Qdrant snapshot + files)'
Push-Location $Root; & $py -m scripts.backup backup; $rc = $LASTEXITCODE; Pop-Location
if ($rc) { throw 'backup falló' }
$bk = (Get-ChildItem (Join-Path $Root 'backups') -Directory -Filter 'alice-*' | Sort-Object Name | Select-Object -Last 1).FullName

Step 'Stop native Qdrant / Prometheus / Grafana (owned PIDs only)'
foreach ($n in 'grafana', 'prometheus', 'qdrant') {
  $id = Get-OwnPid $n
  if ($id) { Stop-Process -Id $id; Wait-Process -Id $id -Timeout 15 -ErrorAction SilentlyContinue; Remove-Item (Join-Path $RunDir "$n.pid") -Force; Write-Host "  stopped $n" }
}

Step 'Compose up'
Invoke-Compose @('up', '-d')
if ($LASTEXITCODE -ne 0) { Write-Warning 'compose up falló -> rollback'; & "$PSScriptRoot\Rollback-Docker.ps1"; exit 1 }
$ok = (Wait-Http 'http://127.0.0.1:6333/healthz' 60) -and (Wait-Http 'http://127.0.0.1:9090/-/ready' 60) -and (Wait-Http 'http://127.0.0.1:3000/api/health' 90)
if (-not $ok) { Write-Warning 'Servicios en contenedor no responden en 127.0.0.1 desde Windows -> rollback'; & "$PSScriptRoot\Rollback-Docker.ps1"; exit 1 }

Step 'Exposure check: container ports must NOT be reachable on LAN / tailnet IPs'
$ips = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -Expand IPAddress)
$open = foreach ($ip in $ips) { foreach ($port in 6333, 6334, 9090, 3000) {
  $c = New-Object Net.Sockets.TcpClient; $hit = $c.ConnectAsync($ip, $port).Wait(1500); $c.Close(); if ($hit) { "${ip}:$port" } } }
if ($open) { Write-Warning "EXPUESTO: $($open -join ', ') -> rollback"; & "$PSScriptRoot\Rollback-Docker.ps1"; exit 1 }
Write-Host "  closed on: $($ips -join ', ')"

Step 'Restore Qdrant collection from the backup snapshot'
$snap = Get-ChildItem (Join-Path $bk 'qdrant') -Filter *.snapshot -ErrorAction SilentlyContinue | Select-Object -First 1
if ($snap) {
  $code = @"
import httpx, sqlite3, sys
from apps.api.config import settings
with open(r'$($snap.FullName)', 'rb') as f:
    r = httpx.post('http://127.0.0.1:6333/collections/alice_chunks/snapshots/upload?wait=true&priority=snapshot', files={'snapshot': f}, timeout=600)
r.raise_for_status()
pts = httpx.get('http://127.0.0.1:6333/collections/alice_chunks').json()['result']['points_count']
n = sqlite3.connect(settings().ops_db).execute('select count(*) from chunks').fetchone()[0]
print(f'qdrant points {pts} / sqlite chunks {n}')
sys.exit(0 if pts == n else 1)
"@
  Push-Location $Root; & $py -c $code; $rc = $LASTEXITCODE; Pop-Location
  if ($rc) { Write-Warning 'Conteo Qdrant != SQLite -> rollback'; & "$PSScriptRoot\Rollback-Docker.ps1"; exit 1 }
}

Step 'Switch Alice to runtime=docker and restart the API'
$envFile = Join-Path $Root '.env'
$lines = Get-Content $envFile | Where-Object { $_ -notmatch '^(ALICE_RUNTIME|DOCKER_CMD)=' }
$lines += 'ALICE_RUNTIME=docker', "DOCKER_CMD=wsl.exe -d $Distro --exec docker"
Set-Content $envFile $lines -Encoding utf8
$id = Get-OwnPid 'alice-api'; if ($id) { Stop-Process -Id $id; Wait-Process -Id $id -Timeout 15 -ErrorAction SilentlyContinue }
& "$PSScriptRoot\Start-Alice.ps1"

Write-Host "`nMigración hecha. Verifica: Test-Alice.ps1 y Demo-Alice.ps1. Deshacer: Rollback-Docker.ps1" -ForegroundColor Green
