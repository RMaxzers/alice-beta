# Operations

All scripts live in `scripts\windows\`, are idempotent, handle paths with spaces, and only touch Alice's own processes (PID files in `storage\run\`).
Run from PowerShell: `powershell -ExecutionPolicy Bypass -File .\scripts\windows\<Script>.ps1` (or directly if your policy allows).

| Script | What it does |
|---|---|
| `Setup-Alice.ps1` | Checks prerequisites; downloads pinned binaries and verifies SHA256; generates `.env` (random secrets, copies OpenRouter/Tavily keys from Hermes' `.env` without printing them, ACL user-only); `uv sync`; pulls missing Ollama models; runs migrations; builds the UI. Safe to re-run: never overwrites `.env` or data |
| `Start-Alice.ps1` | Starts only what is not already running, in order (Ollama → Qdrant → windows_exporter → Alice → Prometheus → Grafana), waits for health, ensures the Grafana viewer, then prints `Status-Alice.ps1` |
| `Stop-Alice.ps1` | Stops only processes Alice started (never an Ollama it found running); no data is deleted |
| `Status-Alice.ps1` | Verified status table (every line from a real probe). Exit code 1 if any core component is down |
| `Test-Alice.ps1` | pytest (unit, security, integration if Alice is up) + router evaluation → `docs/ROUTER-EVAL.md` |
| `Backup-Alice.ps1` | SQLite online backup + Qdrant snapshot + raw/processed files + sha256 manifest → `backups\alice-<ts>\`; keeps newest 7 |
| `Restore-Alice.ps1 -Backup <dir> -Destination <new dir>` | Verifies checksums/integrity/row counts, restores into a new folder, verifies the Qdrant snapshot in a temporary collection. Refuses live-data destinations |
| `Demo-Alice.ps1` | Seeds synthetic samples and rehearses the demo → `docs/DEMO-RUN.md` |

## After a reboot / login
Alice does not auto-start (not tested unattended; Grafana/Qdrant/Alice run as user processes). After logging in:
`Start-Alice.ps1`. Tailscale Serve rules persist across reboots (`--bg`). Ollama's own tray app may also start Ollama; Alice reuses it
(check `ollama ps` → 100 % GPU; if the tray instance was started without `OLLAMA_HOST=127.0.0.1` it still binds loopback by default).

## Ports (all 127.0.0.1)
8000 Alice · 9101 Alice metrics · 11434 Ollama · 6333/6334 Qdrant · 9090 Prometheus · 3000 Grafana · 9182 windows_exporter.
If a port is taken, `Start-Alice.ps1` will fail that component's health check; identify the owner with
`Get-NetTCPConnection -LocalPort <p> | % { Get-Process -Id $_.OwningProcess }` — scripts never kill foreign processes.

## Logs
`logs\alice.jsonl` (Alice, JSON, rotated), `logs\<component>.out.log|err.log` (stdout/stderr of each process), `logs\grafana\`.

## Resource profile (measured 2026-09-22, see SOAK-REPORT.md)
See `docs/STATUS.md` → "Resource usage".

## Updating a pinned binary
Edit version, URL and official SHA256 in `scripts\windows\_common.ps1` (`$Versions`), run `Setup-Alice.ps1`, then `Stop`/`Start`.
