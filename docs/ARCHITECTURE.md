# Alice Beta 0.1 — Architecture (as installed)

## Physical layout
Everything runs natively on the Windows host (decision D1: no WSL2/Docker in this beta, see DECISIONS.md).
All services bind **127.0.0.1**. The only remote entry is Tailscale Serve (tailnet-only, HTTPS).

```text
Laptop (tailnet, authorized)
   │ HTTPS  https://eva01.tail3f8e85.ts.net:8443        (Grafana Viewer: :8444)
   ▼
Tailscale Serve (Windows) ──► 127.0.0.1:8000  Alice API + UI (FastAPI, Python 3.12, uv venv)
                                 │  path allowlist for proxied requests: /, /assets/*, /api/*
                                 │  session cookie (HttpOnly, SameSite=Strict, Secure via Serve) + CSRF
                                 ▼
                          policies → router → tools → providers
   ┌──────────────┬──────────────┬──────────────┬───────────────┬──────────────┐
   ▼              ▼              ▼              ▼               ▼              ▼
 Ollama        Qdrant         SQLite         EgressGate ──► OpenRouter    Prometheus ◄─ windows_exporter :9182
 :11434        :6333          ops + tables   (tickets)  ──► Tavily        :9090     ◄─ Alice metrics  :9101
 qwen3 4B      alice_chunks   (2 files)                                    │           ◄─ Qdrant, Grafana
 bge-m3                                                                    ▼
                                                                         Grafana :3000 (ALICE / OVERVIEW)
```

| Process | Binary / version | Port | Started by |
|---|---|---|---|
| Alice API + UI | Python 3.12.14, FastAPI 0.115, uvicorn | 127.0.0.1:8000 | Start-Alice.ps1 |
| Alice metrics | prometheus_client (same process) | 127.0.0.1:9101 | — |
| Ollama | 0.34.2 (existing install) | 127.0.0.1:11434 | Start-Alice.ps1 if not running |
| Qdrant | 1.19.1 (official Windows zip, SHA256 verified) | 127.0.0.1:6333/6334 | Start-Alice.ps1 |
| Prometheus | 3.14.0 (official zip, SHA256 verified), 7d / 2 GB retention | 127.0.0.1:9090 | Start-Alice.ps1 |
| Grafana OSS | 13.2.2 (official zip, SHA256 verified) | 127.0.0.1:3000 | Start-Alice.ps1 |
| windows_exporter | 0.31.8 (official exe, SHA256 verified) | 127.0.0.1:9182 | Start-Alice.ps1 |

PIDs are recorded in `storage/run/*.pid`; `Stop-Alice.ps1` only stops those PIDs.

## Logical flow of a request
1. **Auth** — session cookie + CSRF header on every mutation; Origin checked.
2. **Effective privacy** — strictest of: message label (PRIVATE by default), history, attachments. Never lowered.
3. **Routing** (`services/router`) — (a) attachments decide first (tabular→SQL, log→log analysis, docs→RAG);
   (b) deterministic regex rules (`config/routing/rules.yaml`); (c) semantic similarity to tuning exemplars (bge-m3);
   (d) qwen3 4B classifier with JSON-schema structured output, validated by Pydantic (`extra=forbid`);
   (e) policy check independent of the LLM (egress routes downgraded to local when cloud/web unavailable or local-only).
4. **Tools** are chosen by code from the route, never from model output:
   - `OBSERVABILITY` → `ObservabilityAnswerer`: templated answers from Prometheus, nvidia-smi, Ollama API, health checks, the request log and the ledger. **No LLM** → no invented figures.
   - `STRUCTURED_QUERY` → the LLM only fills a typed `QueryPlan`; SQL is built by code and executed read-only under `sqlite3.set_authorizer`.
   - `LOG_ANALYSIS` → deterministic parsing/grouping; the LLM only phrases the aggregated summary.
   - `LOCAL_RAG` → local embeddings + Qdrant + verified facts; answers cite `[n]` with page/section.
   - `WEB_RESEARCH` / `FINANCIAL_RESEARCH` → local query rewrite → EgressGate → Tavily → local synthesis with sources and dates.
   - `CLOUD_*` → EgressGate → budget reservation → OpenRouter (no fallbacks) → reconciliation.
5. **Generation** — one local generation at a time (semaphore, queue ≤ 4, backpressure error beyond).
6. **Accounting** — `requests` table (opaque id, timings split into queue/retrieval/provider), `ledger` for cost, Prometheus metrics.

## Egress control (the privacy boundary)
`services/policies/egress.py::EgressGate` is the only code that can mint a `Clearance`. `OpenRouterProvider.stream`
and `WebSearch.search` refuse to send without one and re-verify that the **exact** payload hash and destination match.
Tickets are single-use, user-bound, payload-hash-bound, provider/model-bound, expire in 5 min and carry a cost cap.
There is no cloud fallback path in code. "Solo local" is enforced in the gate (backend), not in the UI.

## Storage
| What | Where |
|---|---|
| Original files | `data/raw/<doc_id>/` |
| Extracted text / events | `data/processed/<doc_id>.json` |
| Vectors | Qdrant collection `alice_chunks` (1024-d cosine, bge-m3), payload: document_id, page/section, privacy |
| Catalog, provenance, chunks text, facts, requests, ledger, tickets, audit | `storage/sqlite/alice.db` (versioned migrations) |
| Imported tables (CSV/XLSX) | `storage/sqlite/tables.db` (separate, read-only for queries) |
| Metrics TSDB | `storage/prometheus` |
| Grafana state | `storage/grafana` |
| Alice logs (JSON lines, rotated 5×5 MB, no prompts/answers) | `logs/alice.jsonl` |

## Alternatives rejected
- WSL2 + Docker Engine / Docker Desktop: hypervisor risk on this machine (D1), VM RAM overhead.
- Moving Ollama into WSL: no benefit; native Windows CUDA works (100 % GPU offload verified).
- Hermes as the research/cloud path: cannot enforce Alice's egress policy inside Hermes (D10).
- LLM-generated PromQL/SQL/Docker commands: replaced by catalogs, typed plans and an allowlisted broker.
- cAdvisor/Alloy/Loki: not needed without Docker; logs are local JSON and the Docker broker covers container logs when Docker exists.
