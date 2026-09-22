# Environment inventory (sanitized)

Taken 2026-09-22, read-only. Secret values were never read or printed; only presence.

## Host
| Item | Observed |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| CPU | Intel Tiger Lake-H engineering sample (reports "Genuine Intel CPU 0000 @ 2.60GHz"), laptop chip on desktop board (ERYING HM570) |
| RAM | 15.8 GB total, ~8.6 GB free at idle with user apps open |
| Disk | C: 496 GB free |
| GPU | NVIDIA GeForce RTX 3070 Laptop GPU, 8192 MiB, nvidia-smi OK, driver 610.47 (INF oem20.inf, 32.0.16.1047, modified "Frankenstein" build for SUBSYS_000010DE) |
| Stability | 6 Kernel-Power 41 unexpected resets in 14 days (08-09, 17-09 x2, 19-09 x3), no bugcheck recorded for them; last BSOD 0xD1 on 03-09 |
| Hypervisor | Not present. VT-d disabled in BIOS |
| WSL | Not installed |
| Docker | Not installed |

## Software
| Item | Observed |
|---|---|
| Ollama | 0.34.2, `%LOCALAPPDATA%\Programs\Ollama`, models in `~\.ollama\models` (2.3 GB): `qwen3:4b-instruct-2507-q4_K_M`, `asistente-local:v1` (derived). No OLLAMA_* env vars. Endpoint 127.0.0.1:11434, was not running at inventory time |
| Open WebUI | Data in `%LOCALAPPDATA%\IA-Lab\OpenWebUI\data`; launcher not found; not listening at inventory time |
| Hermes Agent | v0.21.3 (2026.9.14), git install at `%LOCALAPPDATA%\hermes\hermes-agent`; provider openrouter + local ollama profile; ships an OpenAI-compatible API server (`gateway/platforms/api_server*.py`). `.env` contains OPENROUTER_API_KEY and TAVILY_API_KEY (present, values not shown) |
| Tailscale | 1.102.2, node `eva01` (100.126.106.61). Existing Serve: `https://eva01.tail3f8e85.ts.net/ -> http://127.0.0.1:8080` (tailnet only). Funnel: none. Tailnet includes a device owned by another user |
| GitHub CLI | logged in as RMaxzers, scopes repo/read:org/gist |
| Runtimes | Python 3.14.7 (system), uv (bundled with Hermes), Node 24.19.0, Git 2.55 |

## Listening ports at inventory time
135/445/139 (Windows), 3389 RDP on 0.0.0.0 (pre-existing, not changed by Alice), 443 tailscaled on tailnet IP, 5040/5357/7680 (Windows), 9180 lghub_updater (loopback).

## Environment variables (presence only)
OPENROUTER/ANTHROPIC/OPENAI/DEEPSEEK/GEMINI/GRAFANA/TAVILY: none set at user or machine scope.
