# Security model

## Boundaries
| Boundary | Control | Test |
|---|---|---|
| Content leaving the PC | `EgressGate` single-use tickets bound to user + payload hash + provider/model + 5 min + cost cap; providers re-verify the hash; no fallback path; "Solo local" enforced in backend | `tests/security/test_privacy.py` (critical `PRIVATE_NEVER_LEAVES_HOST_WITHOUT_AUTHORIZATION` + 10 cases), live run in DEMO-RUN step 11 |
| Remote access | Tailscale Serve only (tailnet), no Funnel/port-forward; proxied requests limited to `/`, `/assets/*`, `/api/*` | `tests/integration/test_live.py::test_proxied_requests_cannot_reach_internal_paths`, port scan in REMOTE-DEMO.md |
| API | HMAC-signed session cookie (HttpOnly, SameSite=Strict, Secure behind Serve), CSRF header on all mutations, Origin check, login throttle (5 / 5 min per client), strict Pydantic bodies | `test_api_auth_csrf_and_headers`, `test_login_throttle_is_per_client` |
| Browser | CSP `default-src 'self'` (no inline scripts, no external origins), `frame-ancestors 'none'`, nosniff, no-referrer, no-store on API; safe Markdown renderer (no raw HTML) | headers test |
| Docker | Broker with 4 typed read operations, argv lists, `shell=False`, ID regex + allowlist + live inventory, `--` before refs, bounded logs, projected inspect (no env/cmd/labels). Chat cannot run/exec/stop/rm | `tests/security/test_docker.py` (critical `DOCKER_NATURAL_LANGUAGE_CANNOT_EXECUTE_ARBITRARY_COMMAND`) |
| SQL | LLM fills a typed plan only; identifiers quoted from real schema; values bound; read-only URI; `set_authorizer` allows SELECT/READ on allowed tables + a few functions; 200 rows; 5 s | `tests/unit/test_sql.py` |
| Web reader | http/https only; DNS-resolved IP checked (private, loopback, link-local, CGNAT/tailnet 100.64/10, metadata); each redirect re-validated; 2 MB / 10 s / content-type allowlist | `test_ssrf_blocked` |
| Prompt injection | Documents/web/logs are wrapped as `<datos>` and treated as data; tools and egress are chosen by code, never by model output; LLM cannot grant VERIFIED | `test_case6_injected_document…`, `ataque-inyeccion-DEMO.pdf` |
| Uploads | 50 MB server-side limit, real-type check (magic bytes), extension allowlist, filename sanitised, stored under `data/raw/<id>/`; downloads resolved inside `data/raw` only | `test_size_limit_dedupe_versioning_and_paths`, `test_upload_validation` |
| Secrets | `.env` generated locally, ACL = current user + SYSTEM, gitignored; keys never logged, never sent to the frontend (only "configurada/no configurada") | secret scan before push |
| Metrics | `/metrics` on a separate loopback port 9101, never behind Serve; low-cardinality labels only (no prompts/users/docs/URLs/request ids) | `test_metrics_port_is_loopback_only…` |

## Known limitations (Beta)
- Single local user (`admin`); no multi-user authorization model.
- Web reader has a DNS-rebinding window between the check and the connection (marked `ponytail:` in code).
- Grafana Viewer is exposed to the tailnet with its own login; tailnet ACL restriction is a manual step (REMOTE-DEMO.md).
- RDP (3389) was already listening on all interfaces before Alice; not changed by this project — review separately.
- OpenRouter/Tavily keys were copied from Hermes' `.env` (approved); rotating them means updating both.
