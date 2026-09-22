# Alice — Beta 0.1

Hybrid local/cloud AI gateway for a single Windows PC: deterministic-first routing, local knowledge (RAG, SQL, logs),
privacy-enforced cloud egress, self-observability (Prometheus + Grafana) and tailnet-only remote access.

- **Local**: Ollama `qwen3:4b-instruct-2507` (100 % GPU on an RTX 3070 Laptop 8 GB) + `bge-m3` embeddings.
- **Knowledge**: PDF/Markdown/TXT/LOG → Qdrant with page/section citations; CSV/XLSX → SQLite with typed, read-only queries; verified facts with conflict detection.
- **Privacy**: `PRIVATE` by default; nothing leaves the PC without a single-use, payload-bound authorization. No cloud fallback. "Solo local" mode.
- **Cloud**: OpenRouter (`deepseek/deepseek-v4.1-flash`, `anthropic/claude-sonnet-5`) with budget reservation and cost ledger; Tavily web search.
- **Observability**: Windows host (windows_exporter), GPU (nvidia-smi), Ollama, Alice's own metrics; Grafana dashboard **ALICE / OVERVIEW**; Alice answers questions about itself from real data, without an LLM.
- **Remote**: Tailscale Serve (tailnet only) → Alice `:8443`, Grafana Viewer `:8444`.

## Quick start (Windows)
```powershell
cd C:\Users\cuent\alice
.\scripts\windows\Setup-Alice.ps1     # once (idempotent)
.\scripts\windows\Start-Alice.ps1     # start + verified status
.\scripts\windows\Demo-Alice.ps1      # rehearse the demo
```
Open http://127.0.0.1:8000 (credentials in `.env`: `ALICE_USERNAME` / `ALICE_PASSWORD`).

## Documentation
| Doc | Content |
|---|---|
| [ARCHITECTURE](docs/ARCHITECTURE.md) | What is installed, request flow, egress boundary, storage |
| [ENVIRONMENT](docs/ENVIRONMENT.md) · [DECISIONS](docs/DECISIONS.md) | Inventory and decisions (incl. native runtime without WSL/Docker) |
| [MODELS](docs/MODELS.md) · [ROUTER-EVAL](docs/ROUTER-EVAL.md) | Models, measurements, router accuracy |
| [SECURITY](docs/SECURITY.md) | Boundaries, controls and their tests |
| [OBSERVABILITY](docs/OBSERVABILITY.md) | Metrics, dashboard, self-explanation |
| [CONFIGURATION](docs/CONFIGURATION.md) · [OPERATIONS](docs/OPERATIONS.md) · [BACKUP-RESTORE](docs/BACKUP-RESTORE.md) | Running it |
| [DEMO](docs/DEMO.md) · [DEMO-RUN](docs/DEMO-RUN.md) · [REMOTE-DEMO](docs/REMOTE-DEMO.md) | Demo script, recorded rehearsal, laptop instructions |
| [TEST-REPORT](docs/TEST-REPORT.md) · [SOAK-REPORT](docs/SOAK-REPORT.md) | Test results and sustained-load run |
| [STATUS](docs/STATUS.md) · [PROGRESS](docs/PROGRESS.md) · [ROADMAP](docs/ROADMAP.md) | Where things stand |

## Layout
`apps/api` FastAPI app · `apps/web` React UI · `services/*` router, policies, providers, ingestion, rag, structured_data,
observability, integrations, workers · `packages/schemas` shared contracts · `config/` aliases and routing rules ·
`infra/` Prometheus/Grafana config · `scripts/windows` operations · `tests/` unit, security, integration, routing, e2e ·
`data/samples` synthetic demo data. Runtime data (`data/raw`, `storage/`, `logs/`, `backups/`, `.env`) is never committed.

## License
Not yet chosen by the owner. Third-party components keep their own licenses (Qdrant Apache-2.0, Prometheus Apache-2.0,
Grafana AGPL-3.0 — used unmodified as a separate local service, windows_exporter MIT, Qwen3 Apache-2.0, bge-m3 MIT).
