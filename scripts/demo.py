"""Reproducible demo rehearsal: seeds SYNTHETIC samples, runs the demo script end-to-end against the live API,
checks each step against known ground truth, and writes sanitized evidence to docs/DEMO-RUN.md.
Run: .venv\\Scripts\\python -m scripts.demo   (Alice must be running)
"""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

from apps.api.config import ROOT
from scripts.alice_client import Client

SAMPLES = ROOT / "data" / "samples"
results: list[dict] = []


def text(ev):
    return "".join(e["text"] for e in ev if e["type"] == "token")


def meta(ev):
    r = next((e["decision"] for e in ev if e["type"] == "route"), {})
    d = next((e for e in ev if e["type"] == "done"), {})
    return r, d


def step(n, title, ev, checks: dict[str, bool], note=""):
    r, d = meta(ev)
    ok = all(checks.values())
    results.append({"n": n, "title": title, "route": r.get("route"), "by": r.get("decided_by"), "provider": d.get("provider"),
                    "model": d.get("model"), "latency": d.get("latency_s"), "cost": d.get("cost_usd"), "ok": ok,
                    "checks": checks, "excerpt": text(ev)[:500].replace("\n", " "), "note": note})
    print(f"[{'PASS' if ok else 'FAIL'}] {n}. {title} -> {r.get('route')} / {d.get('provider')} {d.get('model')} {d.get('latency_s')}s "
          + ", ".join(f"{k}={'ok' if v else 'NO'}" for k, v in checks.items()))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    c = Client()
    docs = {d["original_name"]: d for d in c.get("/api/documents")}
    for f in ("informe-auditoria-red-DEMO.pdf", "politica-contrasenas-DEMO.md", "inventario-activos-DEMO.csv", "servicio-DEMO.log"):
        if f not in docs or docs[f]["status"] != "ready":
            c.upload(str(SAMPLES / f))
    for _ in range(90):
        docs = {d["original_name"]: d for d in c.get("/api/documents")}
        if all(docs.get(f, {}).get("status") == "ready" for f in ("informe-auditoria-red-DEMO.pdf", "inventario-activos-DEMO.csv", "servicio-DEMO.log")):
            break
        time.sleep(1)
    facts = c.get("/api/facts", subject="servicio-demo.puerto")["facts"]
    if not facts:
        c.c.post("/api/facts", headers=c.h, json={"subject_key": "servicio-demo.puerto", "statement": "El servidor demo usa el puerto 8443",
                                                   "privacy": "INTERNAL", "verification": "VERIFIED", "source_id": "inventario-demo-v1",
                                                   "source_location": "fila 3", "verified_by": "usuario", "notes": "Hecho sintético de demo"}).raise_for_status()
    pdf_id = docs["informe-auditoria-red-DEMO.pdf"]["document_id"]
    log_id = docs["servicio-DEMO.log"]["document_id"]

    sysinfo = c.get("/api/system")
    core = ["alice_api", "router", "ollama", "qdrant", "prometheus", "grafana", "windows_exporter", "gpu"]
    results.append({"n": 1, "title": "Estado del sistema", "route": "-", "by": "-", "provider": "-", "model": "-", "latency": None, "cost": None,
                    "ok": all(sysinfo["health"][k]["state"] == "healthy" for k in core),
                    "checks": {k: sysinfo["health"][k]["state"] == "healthy" for k in core}, "excerpt": "", "note": ""})
    print(f"[{'PASS' if results[-1]['ok'] else 'FAIL'}] 1. Estado del sistema")

    ev = c.chat("Explícame DHCP en pocas palabras")
    step(2, "Explícame DHCP en pocas palabras", ev, {"LOCAL_SIMPLE": meta(ev)[0].get("route") == "LOCAL_SIMPLE", "ollama": meta(ev)[1].get("provider") == "ollama"})
    ev = c.chat("Genera una función que valide estas direcciones IP")
    step(3, "Función que valide IPs", ev, {"LOCAL_CODE": meta(ev)[0].get("route") == "LOCAL_CODE", "code block": "```" in text(ev)})
    ev = c.chat("¿Cuáles son los hallazgos principales?", document_ids=[pdf_id])
    srcs = [s for e in ev if e["type"] == "sources" for s in e["sources"]]
    step(4, "PDF: hallazgos principales", ev, {"LOCAL_RAG": meta(ev)[0].get("route") == "LOCAL_RAG",
                                               "cita página": any(s.get("location", "").startswith("página") for s in srcs),
                                               "H1 14 switches": "14" in text(ev)})
    ev = c.chat("¿Cuántos activos del inventario están fuera de soporte?")
    step(5, "SQL: activos fuera de soporte", ev, {"STRUCTURED_QUERY": meta(ev)[0].get("route") == "STRUCTURED_QUERY", "=16": "**16**" in text(ev)})
    ev = c.chat("¿Qué contenedor usa más memoria ahora?")
    step(6, "¿Qué contenedor usa más memoria?", ev, {"OBSERVABILITY": meta(ev)[0].get("route") == "OBSERVABILITY",
                                                     "honesto sin Docker": "Docker no instalado" in text(ev)},
         note="Docker no instalado (D1): respuesta honesta, sin datos inventados")
    ev = c.chat("Escribe una explicación detallada, de unas 400 palabras, de cómo funciona el control de congestión de TCP.", force_route="LOCAL_SIMPLE")
    step(7, "Consulta local pesada (carga GPU)", ev, {"ollama": meta(ev)[1].get("provider") == "ollama", "tokens>200": (meta(ev)[1].get("tokens_out") or 0) > 200})
    time.sleep(20)  # let Prometheus take post-request samples (15 s scrape)
    ev = c.chat("¿Qué ocurrió con CPU, RAM y GPU durante mi última consulta?")
    t = text(ev)
    step(8, "¿Qué cambió durante mi última consulta?", ev, {"OBSERVABILITY": meta(ev)[0].get("route") == "OBSERVABILITY",
                                                           "modelo identificado": "qwen3" in t, "GPU util": "GPU util" in t,
                                                           "sin causalidad inventada": "no se mide por proceso" in t or "correlación" in t})
    ev = c.chat("Dame los últimos errores del contenedor de Qdrant.")
    step(9, "Errores del contenedor Qdrant", ev, {"OBSERVABILITY": meta(ev)[0].get("route") == "OBSERVABILITY",
                                                  "honesto sin Docker": "Docker no instalado" in text(ev)})
    ev = c.chat("Investiga las novedades recientes de Ollama.", privacy="PUBLIC")
    srcs = [s for e in ev if e["type"] == "sources" for s in e["sources"]]
    step(10, "Investigación web PUBLIC", ev, {"WEB_RESEARCH": meta(ev)[0].get("route") == "WEB_RESEARCH", "fuentes web": len(srcs) >= 3,
                                              "fechas/URLs": all(s.get("url") for s in srcs)})
    ev = c.chat("Resume los hallazgos del informe con el modelo más potente", document_ids=[pdf_id], force_route="CLOUD_POWERFUL")
    auth = next((e for e in ev if e["type"] == "authorization_required"), None)
    step(11, "Documento PRIVATE hacia cloud -> advertencia", ev,
         {"bloqueado hasta autorizar": auth is not None, "muestra fragmentos": bool(auth and any("fragmento" in f for f in auth["preview"]["fields"])),
          "proveedor+modelo": bool(auth and auth["preview"]["model"] == "anthropic/claude-sonnet-5")})
    ev2 = c.chat("Resume los hallazgos del informe con el modelo más potente", document_ids=[pdf_id], force_route="LOCAL_SIMPLE")
    step("11b", "…Continuar localmente", ev2, {"LOCAL_RAG": meta(ev2)[0].get("route") == "LOCAL_RAG", "ollama": meta(ev2)[1].get("provider") == "ollama"})
    ev = c.chat("¿Cuántas consultas fueron locales y cuánto costó el cloud hoy?")
    step(12, "Consultas locales y coste cloud hoy", ev, {"OBSERVABILITY": meta(ev)[0].get("route") == "OBSERVABILITY", "ledger": "USD" in text(ev)})
    ev = c.chat("Según mis documentos, ¿qué puerto usa el servidor demo?")
    step(13, "Hecho VERIFIED en RAG", ev, {"8443": "8443" in text(ev),
                                           "fuente fact": any(s["kind"] == "fact" for e in ev if e["type"] == "sources" for s in e["sources"])})
    ev = c.chat("¿Cuál es el error más frecuente?", document_ids=[log_id])
    step(14, "Log: error más frecuente", ev, {"LOG_ANALYSIS": meta(ev)[0].get("route") == "LOG_ANALYSIS", "23 veces": "23 veces" in text(ev)})

    passed = sum(r["ok"] for r in results)
    lines = [f"# Demo rehearsal — {datetime.now().strftime('%Y-%m-%d %H:%M')} (America/Santiago)", "",
             f"**{passed}/{len(results)} steps passed.** Synthetic data only. Generated by `scripts/demo.py` against the live local API.", "",
             "| # | Step | Route | By | Provider / model | s | Cost USD | Result | Checks |", "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        chk = ", ".join(f"{k} {'✅' if v else '❌'}" for k, v in r["checks"].items())
        lines.append(f"| {r['n']} | {r['title']} | {r['route']} | {r['by']} | {r['provider']} / {r['model']} | {r['latency'] or ''} | "
                     f"{'' if r['cost'] is None else r['cost']} | {'PASS' if r['ok'] else 'FAIL'} | {chk} |")
    lines += ["", "## Answer excerpts", ""]
    for r in results:
        if r["excerpt"]:
            lines.append(f"**{r['n']}. {r['title']}** — {r['excerpt']}{' _(' + r['note'] + ')_' if r['note'] else ''}\n")
    (ROOT / "docs" / "DEMO-RUN.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{passed}/{len(results)} passed -> docs/DEMO-RUN.md")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
