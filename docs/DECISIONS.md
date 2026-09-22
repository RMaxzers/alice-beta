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
| D13 | 2026-09-22 | Grafana published tailnet-only on Serve :8444 with Viewer login; admin never exposed | Spec's remote dashboard step; Grafana has its own auth; ACL restriction is a user step | Keeping Grafana local only |
| D14 | 2026-09-22 | Web queries are rewritten locally into keywords; the rewritten text is exactly what the authorization shows and what is sent | Raw Spanish sentences returned social-media noise; rewrite is local (no egress) | Sending the literal message |
| D15 | 2026-09-22 | OBSERVABILITY answers are templated from real data with no LLM | Guarantees no invented figures; faster | LLM phrasing over tool output |
| D16 | 2026-09-22 | uvicorn runs with `--no-proxy-headers`; Alice reads the rightmost X-Forwarded-For hop itself and rejects non-loopback peers | Security review: throttle bypass via spoofed XFF; uvicorn's rewrite of request.client broke the loopback guard | Trusting uvicorn proxy headers |
| D17 | 2026-09-22 | Browser E2E uses Playwright with the installed Edge (no browser download) against a throwaway-password test instance | Never type the real password into tooling or transcripts | Using the real credentials |
| D18 | 2026-09-22 | Phase 2 prepared (not executed): Docker Engine in dedicated WSL2 distro, mirrored networking, host-network containers bound to 127.0.0.1, digest-pinned images, broker via `wsl --exec` | See docs/PHASE2-WSL-DOCKER.md | Docker Desktop, bridge networks, TCP daemon |
