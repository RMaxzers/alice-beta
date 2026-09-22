# Remote demo from the laptop (Tailscale)

Alice is published **only inside your tailnet** with Tailscale Serve. No Funnel, no port forwarding, no public IP.

| What | URL | Auth |
|---|---|---|
| Alice UI + API | https://eva01.tail3f8e85.ts.net:8443 | Alice login (user/password in `alice\.env` on the PC: `ALICE_USERNAME` / `ALICE_PASSWORD`) |
| Grafana ALICE / OVERVIEW (read-only) | https://eva01.tail3f8e85.ts.net:8444/d/alice-overview | Grafana user `viewer`, password `GRAFANA_VIEWER_PASSWORD` in `alice\.env` |

Not reachable remotely (verified closed on the tailnet and LAN IPs): Ollama 11434, Qdrant 6333/6334, Prometheus 9090,
Grafana 3000 direct, Alice metrics 9101, windows_exporter 9182, Alice 8000 direct. Through Serve, `/healthz`, `/metrics`,
`/docs` and any non-allowlisted path return 404.

## Before leaving home (on the PC)
1. Keep the PC on and logged in (Alice runs as user processes, not Windows services):
   - Plug in power; disable sleep **for the demo only** (reversible):
     `powercfg /change standby-timeout-ac 0` — restore afterwards with `powercfg /change standby-timeout-ac 30` (or your previous value).
2. Start and check: `powershell -ExecutionPolicy Bypass -File C:\Users\cuent\alice\scripts\windows\Start-Alice.ps1`
   Every line must show HEALTHY/READY/OK/CONFIGURED except known DISABLED/UNAVAILABLE items (Hermes, Docker).
3. Confirm Serve rules: `tailscale serve status` must list :8443 → 127.0.0.1:8000 and :8444 → 127.0.0.1:3000 (and your pre-existing `/` → 8080).
4. **Restrict access with Tailscale ACL (human step, admin console)** — your tailnet contains a device owned by another user.
   In https://login.tailscale.com/admin/acls add a grant so only your own devices reach these ports, e.g.:
   ```json
   "grants": [
     { "src": ["<your-tailscale-login>"], "dst": ["tag:alice"], "ip": ["tcp:8443", "tcp:8444"] }
   ]
   ```
   (tag the PC `tag:alice`, or use its host name as `dst`). Remove any broader rule that allows `*` to this node.
   Even without this, Alice and Grafana still require their own login.

## On the laptop
1. Install Tailscale and log in with **the same Tailscale account** as the PC. Check: `tailscale status` shows `eva01`.
2. Open https://eva01.tail3f8e85.ts.net:8443 in the browser → Alice login.
3. Walk through `docs/DEMO.md`.
4. For Grafana, open https://eva01.tail3f8e85.ts.net:8444/d/alice-overview and log in as `viewer`.

## Verification done from the PC (2026-09-22)
- HTTPS via Serve: login OK, session cookie `Secure`, `via_proxy: true`, chat streaming OK.
- Grafana via Serve: anonymous → 401; `viewer` login OK; dashboard + panel queries OK; admin API denied.
- Direct TCP to internal ports on 100.126.106.61 and 192.168.1.8: all closed.

**PENDING (needs you):** test from the laptop on a different network (e.g. phone hotspot), and verify that a device
outside your ACL cannot connect. Loopback/tailnet-IP tests from the PC do not prove external reachability.

## Troubleshooting
- Page does not load: `tailscale status` on both machines; on the PC run `Status-Alice.ps1`.
- 401 after a while: session expires in 12 h; log in again.
- Remove only Alice's Serve rules: `tailscale serve --https=8443 off` and `tailscale serve --https=8444 off`
  (never `tailscale serve reset`, which would also remove the pre-existing `/` rule).

## If Internet fails during the demo
Local chat, RAG, SQL, logs and observability keep working **on the PC** (models and assets are local). The laptop
needs connectivity to reach the PC; if it's lost, continue on the PC screen or show `docs/DEMO-RUN.md` (recorded evidence, labelled).
