# Status — 2026-09-22

**Overall: PARTIAL** — core and full local demo verified; items marked PENDING need the user or a later phase.

| Area | State | Note |
|---|---|---|
| Local AI | READY | qwen3 4B + bge-m3, 100 % GPU |
| Router | READY | 52/52 eval; rules + semantic + classifier + policy |
| Knowledge | READY | PDF, MD, TXT, LOG, CSV, XLSX; Qdrant + SQLite; verified facts |
| Observability | READY | Windows host, GPU, Ollama, Alice metrics; self-explanation from real data |
| Docker | NOT INSTALLED (by decision D1) | broker ready; phase 2 PREPARED (docs/PHASE2-WSL-DOCKER.md), needs admin + reboot |
| Grafana | READY | ALICE / OVERVIEW; tailnet Viewer on :8444 |
| Cloud | READY | OpenRouter real calls OK; budget 0.05 / 1.00 USD; Tavily OK |
| Remote access | CONFIGURED, external test PENDING | Serve :8443/:8444 verified from the PC; laptop-on-other-network test and tailnet ACL are user steps |
| Tests | PASS | 70 pytest, 16 E2E, 15/15 demo, 30-min soak |
| Security | PASS | gitleaks clean; review finding fixed |

## Resource usage (measured)
- Idle, models unloaded: Alice stack ≈ 0.66 GB RAM (Grafana 305 MB, Prometheus 105, Qdrant 88, API 82, Ollama 53, exporter 29); VRAM 722 MiB (desktop/other apps); RAM free 8.8 / 15.8 GB with the user's apps open.
- Models loaded: +3.6 GiB VRAM (qwen3 3.0 + bge-m3 0.6) → ~4.8 GB used of 8.
- Under 30-min mixed load: RAM available ≥ 6.4 GiB, VRAM ≤ 4.9 GB, GPU ≤ 42 °C, 0 errors, 0 resets.

## Next concrete actions (user)
1. Laptop test from another network (docs/REMOTE-DEMO.md).
2. Tailnet ACL restricting :8443/:8444 to your devices (admin console).
3. Decide on the WSL2/Docker phase (needs reboot) after watching machine stability.
