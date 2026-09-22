# Decisions

| # | Date | Decision | Why | Rejected |
|---|---|---|---|---|
| D1 | 2026-09-22 | Qdrant, Prometheus, Grafana and windows_exporter run as **native Windows binaries** bound to 127.0.0.1. No WSL2/Docker in Beta 0.1 | WSL not installed; enabling it turns on the hypervisor and needs a reboot. On this machine the hypervisor was a boot-loop suspect, and there are recent hard resets. Native binaries also avoid the ~1-2 GB WSL VM overhead. User approved | WSL2 + Docker Engine; Docker Desktop |
| D2 | 2026-09-22 | DockerAdapter is implemented and tested against a fake runner; runtime status is `unavailable: Docker not installed` | Follows D1; the adapter is ready for a later WSL2/Docker phase | Faking container data |
| D3 | 2026-09-22 | Keep Ollama native on Windows; reuse `qwen3:4b-instruct-2507-q4_K_M` for local-general and local-code | Already installed and ~3-4B as the spec suggests; avoid extra downloads | Separate code model (VRAM) |
| D4 | 2026-09-22 | Embeddings: `bge-m3` via Ollama | Multilingual (Spanish), local, MIT license | nomic-embed-text (English-centric) |
| D5 | 2026-09-22 | Router = rules → semantic similarity → qwen3 JSON-schema classifier only for ambiguous cases | No extra classifier model in VRAM; deterministic policies take precedence | A dedicated classifier model |
| D6 | 2026-09-22 | OpenRouter and Tavily keys are copied from Hermes' `.env` into `alice/.env` (ACL for the current user only) | User approved; Alice must not depend on Hermes at runtime | Reading Hermes' `.env` at runtime |
| D7 | 2026-09-22 | Budget USD 0.05/request and 1.00/day | User approved | — |
| D8 | 2026-09-22 | Remote: Tailscale Serve `https=8443 -> 127.0.0.1:8000`; existing `/ -> :8080` rule untouched | User approved; preserves Open WebUI publishing | Replacing the root rule |
| D9 | 2026-09-22 | Alice metrics on a separate loopback port (9101) | `/metrics` can never be reachable through the Serve entry | Path filtering on the same port |
| D10 | 2026-09-22 | HermesAdapter is health-only and DISABLED by default | The Hermes profile enables terminal/code execution and cloud auxiliary models; Alice cannot enforce its egress policy on them | Routing research through Hermes |
| D11 | 2026-09-22 | Backend Python 3.12 in a uv-managed venv | Python 3.14 is new; wheel availability for native deps | System Python 3.14 |
| D12 | 2026-09-22 | GPU metrics are sampled by Alice from `nvidia-smi` (fixed argv) | No official NVIDIA exporter for Windows here; smallest thing that works. Limitation: no GPU series while Alice is down | DCGM (Linux/datacenter only) |
