# Changelog

## 0.1.0-beta.1 — 2026-09-22
First beta.
- Native Windows runtime: Ollama, Qdrant 1.19.1, Prometheus 3.14.0, Grafana 13.2.2, windows_exporter 0.31.8 (pinned, SHA256-verified).
- Hybrid router (rules → semantic → local classifier → policy) with 52 labelled evaluation cases.
- EgressGate: payload-bound single-use authorization tickets; OpenRouter and Tavily only through it; "Solo local" mode.
- Knowledge: PDF/MD/TXT/LOG ingestion with citations, CSV/XLSX typed SQL, log analysis, verified facts with conflicts.
- Observability: Alice metrics, GPU/Ollama samplers, host metrics, ALICE / OVERVIEW dashboard, deterministic self-explanation.
- Restricted Docker broker (ready; Docker not installed in this beta).
- React UI (Chat, Knowledge, Observability, Models, System, Settings), tailnet access via Tailscale Serve.
- Scripts: Setup/Start/Stop/Status/Test/Backup/Restore/Demo.
