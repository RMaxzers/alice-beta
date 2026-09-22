# Test report — Alice 0.1.0-beta.1 (2026-09-22)

Environment: Windows 11 Pro 26200, RTX 3070 Laptop 8 GB (driver 32.0.16.1047 modified), Python 3.12.14, Ollama 0.34.2,
Qdrant 1.19.1, Prometheus 3.14.0, Grafana 13.2.2, windows_exporter 0.31.8. Synthetic data only.

| Area | Evidence | Result |
|---|---|---|
| Unit + security + integration (pytest) | `Test-Alice.ps1` → 70 tests (unit, security, live integration against the running stack) | **PASS 70/70** |
| Critical: PRIVATE_NEVER_LEAVES_HOST_WITHOUT_AUTHORIZATION | `tests/security/test_privacy.py` (httpx transport recorder, 0 content POSTs to non-loopback without ticket) + 10 privacy cases (§21.2) | **PASS** |
| Critical: DOCKER_NATURAL_LANGUAGE_CANNOT_EXECUTE_ARBITRARY_COMMAND | `tests/security/test_docker.py` (argv inspection, injection strings, flag-looking IDs, foreign container, forbidden verbs) | **PASS** |
| Critical: OBSERVABILITY_RESPONSES_USE_REAL_DATA | `tests/integration/test_live.py` — Alice's RAM/VRAM/loaded-model answers compared to independent reads of Prometheus, nvidia-smi and Ollama | **PASS** |
| Router (≥ 30 cases) | `docs/ROUTER-EVAL.md`: 52 cases (40 eval + 12 held-out), p95 1.1 s, 0 malformed | **PASS 52/52** (see caveat on semantic tier) |
| Local inference on GPU | `ollama ps` 100 % GPU; GPU util 27 → 92 % during long generation | **PASS** |
| RAG (PDF, Markdown) with citations | DEMO-RUN steps 4, 11b, 13 | **PASS** |
| SQL (CSV) | 16/40 out-of-support (ground truth 16); authorizer blocks DELETE/ATTACH/PRAGMA/other tables/multi-statement | **PASS** |
| Logs | most frequent error 23× (ground truth 23); secret redaction | **PASS** |
| Verified knowledge | VERIFIED fact used with source; conflicting VERIFIED facts surfaced; LLM cannot grant VERIFIED | **PASS** |
| Cloud (real) | OpenRouter Sonnet 5 (authorized once, USD 0.00173 reported) and DeepSeek v4.1 flash (PUBLIC, USD 0.000126); tampered/reused/unapproved tickets rejected | **PASS** |
| Web research (real) | Tavily with locally rewritten query; PRIVATE query requires authorization | **PASS** |
| Observability | Prometheus targets 5/5 up; 31-panel dashboard, every query executed (3 event-counters show "sin datos" until events occur) | **PASS** |
| Docker | Adapter tested with fake runner; runtime Docker not installed (D1) → honest "not installed" answers | **PARTIAL** (by decision) |
| UI (browser) | `tests/e2e/ui_smoke.py`, installed Edge headless: login, bad password, streaming, details, SQL, authorization modal + continue locally, all screens, mobile 375 px no overflow, no CSP/JS errors | **PASS 16/16** |
| Remote access | Serve :8443/:8444 tailnet-only; HTTPS login with Secure cookie through the tailnet URL; internal ports closed on tailnet and LAN IPs; proxied internal paths 404 | **PASS from the PC** · external laptop test **PENDING (user)** |
| Backup/restore | real backup → restore to %TEMP% (checksums, integrity, counts, Qdrant snapshot into temp collection); refusal on live path | **PASS** |
| Demo rehearsal | `docs/DEMO-RUN.md` | **PASS 15/15** |
| Sustained load (30 min) | `docs/SOAK-REPORT.md`: 90 requests, 0 errors, min RAM available 6.4 GiB, VRAM ≤ 4.9 GB, GPU ≤ 42 °C, **0** Kernel-Power 41 / TDR / WHEA events | **PASS** |
| Secret scan | gitleaks 8.30.1 on full history + staged: clean (1 justified false positive: synthetic test string, `.gitleaksignore`) | **PASS** |
| Independent security review (read-only agent) | Confirmed 1 issue: login throttle bypass via spoofed `X-Forwarded-For` → fixed (rightmost hop + global cap), regression test added. Also added loopback-only peer guard; this surfaced that uvicorn rewrote `request.client` from XFF → now `--no-proxy-headers` | **FIXED** |

## Bugs found and fixed during validation
- SSRF guard missed the CGNAT/tailnet range 100.64.0.0/10 (unit test).
- Log redaction marker lost its closing bracket (self-check).
- Concurrent Qdrant collection creation → 409 (live ingestion); lock + tolerate 409; retry endpoint.
- RAG similarity floor hid an explicitly attached PDF (live demo) → no floor when the user chooses the document.
- Grounded system prompt made the 4B model refuse a plain coding task → split prompts.
- Web search quality with the raw Spanish sentence → local query rewrite (preview shows the exact query).
- UI Observability screen crashed on a contract mismatch → fixed + per-screen error boundary.
- Login throttle bypass (security review) and uvicorn proxy-header rewriting.

## Not tested / limits
- From a laptop on another network; an unauthorized tailnet device (needs user + ACL change).
- Unattended start after reboot (not configured).
- Offline mode (Internet unplugged) not physically tested; local paths make no external calls by design and by test.
- Hermes execution (disabled by policy); Docker/container metrics (not installed).
