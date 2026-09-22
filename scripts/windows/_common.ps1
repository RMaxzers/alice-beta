# Shared helpers for Alice Windows scripts. Dot-source only.
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$Script:Root   = (Resolve-Path "$PSScriptRoot\..\..").Path
$Script:Bin    = Join-Path $Root 'infra\bin'
$Script:RunDir = Join-Path $Root 'storage\run'
$Script:LogDir = Join-Path $Root 'logs'
$Script:Ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
$Script:Uv     = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $Uv) { $Script:Uv = Join-Path $env:LOCALAPPDATA 'hermes\bin\uv.exe' }

# Pinned versions + official SHA256 (release checksum files / GitHub asset digest).
$Script:Versions = @{
  qdrant     = @{ ver='1.19.1';  url='https://github.com/qdrant/qdrant/releases/download/v1.19.1/qdrant-x86_64-pc-windows-msvc.zip'; sha='9b6f69bd85f6abed4bc13f943099f55c6ffd55f5dd90388635320d8fbb569eb0' }
  prometheus = @{ ver='3.14.0';  url='https://github.com/prometheus/prometheus/releases/download/v3.14.0/prometheus-3.14.0.windows-amd64.zip'; sha='e57fbb99e4d0bc734d2f2b3aeb68c02fba38862259dc99a95c27ea46d9ccba0a' }
  grafana    = @{ ver='13.2.2';  url='https://dl.grafana.com/oss/release/grafana-13.2.2.windows-amd64.zip'; sha='7f2854e288c12395ad0170368bfc77c0c192a6d98ae6c3452917055cfd78b8cf' }
  winexp     = @{ ver='0.31.8';  url='https://github.com/prometheus-community/windows_exporter/releases/download/v0.31.8/windows_exporter-0.31.8-amd64.exe'; sha='03bb0fe80b8ad0b4e39606b96c4c5cc56b1f766760011ea2b00111157c6ef077' }
}

function Read-DotEnv([string]$Path = (Join-Path $Root '.env')) {
  $h = @{}
  if (Test-Path $Path) {
    foreach ($l in Get-Content $Path) {
      if ($l -match '^\s*([A-Za-z0-9_]+)\s*=(.*)$') { $h[$Matches[1]] = $Matches[2].Trim() }
    }
  }
  $h
}

function Test-Http([string]$Url, [int]$TimeoutSec = 3) {
  try { $r = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing; return $r.StatusCode -lt 400 } catch { return $false }
}

function Get-OwnPid([string]$Name) {
  $f = Join-Path $RunDir "$Name.pid"
  if (-not (Test-Path $f)) { return $null }
  $id = [int](Get-Content $f)
  $p = Get-Process -Id $id -ErrorAction SilentlyContinue
  if ($p) { return $id } else { Remove-Item $f -Force; return $null }
}

function Start-Owned([string]$Name, [string]$Exe, [string[]]$ArgList, [hashtable]$Env = @{}, [string]$WorkDir = $Root) {
  if (Get-OwnPid $Name) { return }
  foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }
  $p = Start-Process -FilePath $Exe -ArgumentList $ArgList -WorkingDirectory $WorkDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "$Name.out.log") -RedirectStandardError (Join-Path $LogDir "$Name.err.log")
  foreach ($k in $Env.Keys) { Remove-Item "env:$k" -ErrorAction SilentlyContinue }
  $p.Id | Set-Content (Join-Path $RunDir "$Name.pid")
}

function Wait-Http([string]$Url, [int]$Seconds = 30) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  while ((Get-Date) -lt $deadline) { if (Test-Http $Url) { return $true }; Start-Sleep -Milliseconds 500 }
  $false
}
