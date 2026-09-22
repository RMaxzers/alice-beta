"""Integration tests against the running local stack (Start-Alice.ps1). Skipped if Alice is not up."""
from __future__ import annotations

import re
import time

import httpx
import pytest

from apps.api.config import settings

BASE = "http://127.0.0.1:8000"
pytestmark = pytest.mark.integration


def _up() -> bool:
    try:
        return httpx.get(f"{BASE}/healthz", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


if not _up():
    pytest.skip("Alice no está corriendo (Start-Alice.ps1)", allow_module_level=True)


@pytest.fixture(scope="module")
def client():
    from scripts.alice_client import Client
    return Client()


def _text(events):
    return "".join(e["text"] for e in events if e["type"] == "token")


def test_OBSERVABILITY_RESPONSES_USE_REAL_DATA(client):
    """Alice's figures must match an independent read of the same sources."""
    ev = client.chat("¿Cuánta CPU y RAM está usando el sistema?")
    assert ev[0]["decision"]["route"] == "OBSERVABILITY"
    txt = _text(ev)
    used_alice = float(re.search(r"RAM usada: ([\d.]+) GiB", txt).group(1))
    r = httpx.get("http://127.0.0.1:9090/api/v1/query",
                  params={"query": "windows_memory_physical_total_bytes - windows_memory_available_bytes"}).json()
    used_prom = float(r["data"]["result"][0]["value"][1]) / 1024 ** 3
    assert abs(used_alice - used_prom) < 0.6, (used_alice, used_prom)   # 15 s scrape drift tolerance

    ev = client.chat("¿Cuánta VRAM estoy utilizando?")
    txt = _text(ev)
    vram_alice = float(re.search(r"VRAM: (\d+) / (\d+) MiB", txt).group(1))
    import subprocess
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    assert abs(vram_alice - float(out.split()[0])) < 400

    ev = client.chat("¿Qué modelo está cargado en Ollama?")
    loaded = httpx.get("http://127.0.0.1:11434/api/ps").json()["models"]
    for m in loaded:
        assert m["name"] in _text(ev)


async def test_missing_source_is_reported_not_zero():
    from services.observability.prometheus import PromError, PrometheusAdapter
    with pytest.raises(PromError):
        await PrometheusAdapter("http://127.0.0.1:1").instant("host_cpu_percent")


def test_health_is_real(client):
    h = client.get("/api/system")["health"]
    for k in ("ollama", "qdrant", "prometheus", "grafana"):
        assert h[k]["state"] == "healthy", (k, h[k])
    assert h["docker"]["state"] == "unavailable"          # honest: Docker not installed (D1)
    assert h["hermes"]["state"] == "disabled"
    t = httpx.get("http://127.0.0.1:9090/api/v1/targets").json()["data"]["activeTargets"]
    assert {x["labels"]["job"] for x in t if x["health"] == "up"} >= {"alice", "windows", "prometheus", "qdrant", "grafana"}


def test_api_auth_csrf_and_headers(client):
    anon = httpx.Client(base_url=BASE)
    assert anon.get("/api/documents").status_code == 401
    assert anon.post("/api/chat", json={"message": "hola"}).status_code == 401
    # authenticated but without CSRF header
    r = client.c.post("/api/chat", json={"message": "hola"})
    assert r.status_code == 403
    r = client.c.post("/api/chat", json={"message": "hola"}, headers={**client.h, "origin": "https://evil.example"})
    assert r.status_code == 403
    h = anon.get("/").headers
    assert "frame-ancestors 'none'" in h["content-security-policy"] and h["x-content-type-options"] == "nosniff"
    assert anon.post("/api/login", json={"username": "admin", "password": "x", "extra": 1}).status_code == 422


def test_proxied_requests_cannot_reach_internal_paths():
    via_serve = {"x-forwarded-for": "100.80.253.88", "tailscale-user-login": "someone@example.com"}
    assert httpx.get(f"{BASE}/healthz", headers=via_serve).status_code == 404
    assert httpx.get(f"{BASE}/metrics", headers=via_serve).status_code == 404
    assert httpx.get(f"{BASE}/docs", headers=via_serve).status_code == 404
    assert httpx.get(f"{BASE}/api/session", headers=via_serve).status_code == 401  # allowed path, still needs auth


def test_login_throttle_is_per_client():
    hdr = {"x-forwarded-for": f"198.51.100.{__import__('secrets').randbelow(250) + 1}"}  # fresh client per run
    codes = [httpx.post(f"{BASE}/api/login", json={"username": "admin", "password": "wrong"}, headers=hdr).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_login_throttle_cannot_be_bypassed_by_spoofed_xff():
    """Serve appends the real peer as the LAST hop; rotating the client-controlled first hop must not reset the bucket."""
    real = f"100.64.{__import__('secrets').randbelow(250)}.{__import__('secrets').randbelow(250) + 1}"
    codes = [httpx.post(f"{BASE}/api/login", json={"username": "admin", "password": "wrong"},
                        headers={"x-forwarded-for": f"203.0.113.{i}, {real}"}).status_code for i in range(6)]
    assert codes[5] == 429, codes


def test_metrics_port_is_loopback_only_and_not_on_api_port():
    assert "alice_requests_total" in httpx.get("http://127.0.0.1:9101/metrics").text
    assert httpx.get(f"{BASE}/metrics").status_code in (401, 404, 503) or "alice_requests_total" not in httpx.get(f"{BASE}/metrics").text


def test_upload_validation(client):
    r = client.c.post("/api/documents", files={"file": ("x.pdf", b"not a pdf")}, headers=client.h)
    assert r.status_code == 422
    r = client.c.post("/api/documents", files={"file": ("x.exe", b"MZ")}, headers=client.h)
    assert r.status_code == 422


def test_local_generation_uses_gpu(client):
    ev = client.chat("Responde solo: ok", force_route="LOCAL_SIMPLE")
    assert any(e["type"] == "done" and e["provider"] == "ollama" for e in ev)
    ps = httpx.get("http://127.0.0.1:11434/api/ps").json()["models"]
    qwen = next(m for m in ps if m["name"].startswith("qwen3"))
    assert qwen["size_vram"] == qwen["size"], "model not fully on GPU"


def test_rag_sql_logs_against_samples(client):
    docs = {d["original_name"]: d for d in client.get("/api/documents")}
    if "informe-auditoria-red-DEMO.pdf" not in docs:
        pytest.skip("demo samples not ingested (Demo-Alice.ps1)")
    ev = client.chat("¿Cuáles son los hallazgos principales?", document_ids=[docs["informe-auditoria-red-DEMO.pdf"]["document_id"]])
    srcs = [s for e in ev if e["type"] == "sources" for s in e["sources"]]
    assert any(s["location"] == "página 1" for s in srcs)
    assert "14" in _text(ev)
    ev = client.chat("¿Cuántos activos del inventario están fuera de soporte?")
    assert "**16**" in _text(ev)
    ev = client.chat("¿Cuál es el error más frecuente?", document_ids=[docs["servicio-DEMO.log"]["document_id"]])
    assert "23 veces" in _text(ev) and "db-primary" in _text(ev)
