<#
.SYNOPSIS  Idempotent setup for Alice Beta 0.1 (native Windows runtime, see docs/DECISIONS.md D1).
           Never deletes data; re-running only fills in what is missing.
#>
. "$PSScriptRoot\_common.ps1"

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

Step 'Prerequisites'
foreach ($t in @(@{n='uv';p=$Uv}, @{n='ollama';p=$Ollama}, @{n='node';p=(Get-Command node -ea 0).Source}, @{n='nvidia-smi';p=(Get-Command nvidia-smi -ea 0).Source})) {
  if (-not $t.p -or -not (Test-Path $t.p)) { throw "Missing prerequisite: $($t.n)" }
  Write-Host ("  {0,-11} {1}" -f $t.n, $t.p)
}
New-Item -ItemType Directory -Force -Path $Bin, $RunDir, $LogDir, (Join-Path $Root 'storage\sqlite'), (Join-Path $Root 'storage\qdrant'), (Join-Path $Root 'storage\prometheus'), (Join-Path $Root 'storage\grafana') | Out-Null

Step 'Native binaries (pinned + SHA256 verified)'
foreach ($name in $Versions.Keys) {
  $v = $Versions[$name]; $dest = Join-Path $Bin "$name-$($v.ver)"
  if (Test-Path $dest) { Write-Host "  $name $($v.ver) present"; continue }
  $file = Join-Path $Bin ([IO.Path]::GetFileName($v.url))
  if (-not (Test-Path $file)) { Write-Host "  downloading $name $($v.ver)"; Invoke-WebRequest $v.url -OutFile $file -UseBasicParsing }
  $sha = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
  if ($sha -ne $v.sha) { Remove-Item $file -Force; throw "Checksum mismatch for $name ($sha)" }
  New-Item -ItemType Directory -Force $dest | Out-Null
  if ($file.EndsWith('.zip')) { Expand-Archive $file -DestinationPath $dest -Force } else { Copy-Item $file $dest }
  Remove-Item $file -Force
  Write-Host "  $name $($v.ver) installed (sha256 ok)"
}

Step '.env (secrets generated locally, never printed)'
$envFile = Join-Path $Root '.env'
function New-Secret([int]$bytes = 24) { -join ([Security.Cryptography.RandomNumberGenerator]::GetBytes($bytes) | ForEach-Object { $_.ToString('x2') }) }
if (-not (Test-Path $envFile)) {
  $lines = Get-Content (Join-Path $Root '.env.example')
  $gen = @{ ALICE_PASSWORD = (New-Secret 12); ALICE_SESSION_SECRET = (New-Secret 32); GRAFANA_ADMIN_PASSWORD = (New-Secret 16); GRAFANA_VIEWER_PASSWORD = (New-Secret 12) }
  # Copy approved credentials from Hermes (D6) without echoing them.
  $hermes = Read-DotEnv (Join-Path $env:LOCALAPPDATA 'hermes\.env')
  foreach ($k in 'OPENROUTER_API_KEY', 'TAVILY_API_KEY') { if ($hermes[$k]) { $gen[$k] = $hermes[$k].Trim('"', "'") } }
  $ts = (& tailscale status --json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue)
  if ($ts) { $gen['ALICE_PUBLIC_ORIGIN'] = 'https://' + $ts.Self.DNSName.TrimEnd('.') + ':8443' }
  $out = foreach ($l in $lines) {
    if ($l -match '^([A-Z0-9_]+)=' -and $gen.ContainsKey($Matches[1])) { "$($Matches[1])=$($gen[$Matches[1]])" } else { $l }
  }
  Set-Content -Path $envFile -Value $out -Encoding utf8
  Write-Host "  created .env; copied from Hermes: $((@('OPENROUTER_API_KEY','TAVILY_API_KEY') | Where-Object { $gen[$_] }) -join ', ')"
} else { Write-Host '  .env exists, left untouched' }
# Restrict ACL to current user + SYSTEM.
icacls $envFile /inheritance:r /grant:r "$($env:USERNAME):(R,W)" "SYSTEM:(F)" | Out-Null

Step 'Python venv (uv, Python 3.12)'
Push-Location $Root; & $Uv sync --quiet; if ($LASTEXITCODE) { throw 'uv sync failed' }; Pop-Location

Step 'Ollama models'
$needStop = $false
if (-not (Test-Http 'http://127.0.0.1:11434/api/version')) {
  Start-Owned 'ollama' $Ollama @('serve') @{ OLLAMA_HOST = '127.0.0.1:11434'; OLLAMA_MAX_LOADED_MODELS = '2'; OLLAMA_NUM_PARALLEL = '1' }
  $null = Wait-Http 'http://127.0.0.1:11434/api/version' 30; $needStop = $true
}
$have = (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags').models.name
foreach ($m in 'qwen3:4b-instruct-2507-q4_K_M', 'bge-m3:latest') {
  if ($have -contains $m) { Write-Host "  $m present" } else { & $Ollama pull $m }
}

Step 'Database migrations'
Push-Location $Root; & $Uv run --quiet python -m apps.api.migrate; if ($LASTEXITCODE) { throw 'migrations failed' }; Pop-Location

Step 'Web UI build'
$web = Join-Path $Root 'apps\web'
if (Test-Path (Join-Path $web 'package.json')) {
  Push-Location $web
  if (Test-Path 'package-lock.json') { npm ci --no-audit --no-fund --loglevel=error } else { npm install --no-audit --no-fund --loglevel=error }
  npm run build --silent; if ($LASTEXITCODE) { Pop-Location; throw 'web build failed' }
  Pop-Location
}

Write-Host "`nSetup complete. Next: scripts\windows\Start-Alice.ps1" -ForegroundColor Green
