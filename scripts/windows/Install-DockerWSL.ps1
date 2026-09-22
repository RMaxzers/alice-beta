<#
.SYNOPSIS  Phase 2 / stage 2 (no admin): dedicated WSL2 distro 'alice-ubuntu' + Docker Engine + Compose, then pulls the
           pinned images. Does NOT touch the running native services (that is Migrate-ToDocker.ps1).
           Refuses to run unless Check-PostReboot.ps1 passes.
#>
. "$PSScriptRoot\_common.ps1"
function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

Step 'Checkpoint: Check-PostReboot.ps1 must pass'
& "$PSScriptRoot\Check-PostReboot.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Checkpoint falló: no se instala nada.' }

Step '.wslconfig (VM limits + mirrored networking)'
$cfg = Join-Path $env:USERPROFILE '.wslconfig'
if (-not (Test-Path $cfg)) {
  Copy-Item (Join-Path $Root 'infra\wsl\wslconfig') $cfg
  Write-Host "  created $cfg (4 GB RAM, 4 CPU, mirrored)"
} else {
  Write-Warning "$cfg ya existe: NO se modifica. Compáralo con infra\wsl\wslconfig (se requiere networkingMode=mirrored)."
}

Step "Distro '$Distro' from the official Ubuntu 24.04 WSL image (sha256 verified)"
if (-not (Test-DistroRegistered)) {
  $base = 'https://cloud-images.ubuntu.com/wsl/releases/24.04/current'
  $name = 'ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz'
  $tar = Join-Path $Root "work\$name"
  New-Item -ItemType Directory -Force (Split-Path $tar), $WslHome | Out-Null
  $sums = (Invoke-WebRequest "$base/SHA256SUMS" -UseBasicParsing).Content
  $expected = ($sums -split "`n" | Where-Object { $_ -match [regex]::Escape($name) } | ForEach-Object { ($_ -split '\s+')[0] })
  if (-not $expected) { throw "No hay checksum publicado para $name" }
  if (-not (Test-Path $tar)) { Invoke-WebRequest "$base/$name" -OutFile $tar -UseBasicParsing }
  $got = (Get-FileHash $tar -Algorithm SHA256).Hash.ToLower()
  if ($got -ne $expected) { Remove-Item $tar -Force; throw "Checksum distinto ($got)" }
  & wsl.exe --import $Distro $WslHome $tar --version 2
  if ($LASTEXITCODE -ne 0) { throw 'wsl --import falló' }
  Remove-Item $tar -Force
} else { Write-Host '  already registered' }

Step 'Base config: wsl.conf (systemd, default user alice), user'
$wslconf = ConvertTo-WslPath (Join-Path $Root 'infra\wsl\wsl.conf')
& wsl.exe -d $Distro -u root --exec cp $wslconf /etc/wsl.conf
& wsl.exe -d $Distro -u root --exec sh -c 'id alice >/dev/null 2>&1 || useradd -m -s /bin/bash alice'
& wsl.exe --terminate $Distro | Out-Null   # apply systemd + default user

Step 'Docker Engine + Compose (official apt repo)'
& wsl.exe -d $Distro -u root --exec bash (ConvertTo-WslPath (Join-Path $Root 'scripts\linux\install-docker.sh')) alice
if ($LASTEXITCODE -ne 0) { throw 'install-docker.sh falló' }
& wsl.exe --terminate $Distro | Out-Null   # new group membership for alice

Step 'Verify: networking mode, docker as alice (no sudo), daemon not on TCP'
$mode = (& wsl.exe -d $Distro --exec wslinfo --networking-mode 2>$null) -replace "`0", ''
if ($mode.Trim() -ne 'mirrored') { throw "networking mode = '$mode' (se requiere mirrored; revisa .wslconfig y ejecuta wsl --shutdown)" }
& wsl.exe -d $Distro --exec docker version --format 'docker {{.Server.Version}} (as alice)'
if ($LASTEXITCODE -ne 0) { throw 'docker no responde como usuario alice' }
$tcp = & wsl.exe -d $Distro --exec sh -c 'ss -ltnp 2>/dev/null | grep -E ":2375|:2376" || true'
if ($tcp) { throw "El daemon Docker escucha en TCP: $tcp" }

Step 'Pull pinned images (by digest)'
Invoke-Compose @('pull')
if ($LASTEXITCODE -ne 0) { throw 'compose pull falló' }

Write-Host "`nListo. Los servicios nativos siguen activos. Siguiente: Migrate-ToDocker.ps1" -ForegroundColor Green
