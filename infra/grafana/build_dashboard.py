"""Builds infra/grafana/dashboards/alice-overview.json from real, verified series names.
Run: uv run python infra/grafana/build_dashboard.py
"""
import json
from pathlib import Path

DS = {"type": "prometheus", "uid": "alice-prometheus"}
panels, y = [], 0


def row(title):
    global y
    panels.append({"type": "row", "title": title, "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "collapsed": False})
    y += 1


def ts(title, targets, unit, x, w=8, h=8, desc="", stack=False, maxv=None):
    p = {"type": "timeseries", "title": title, "description": desc, "datasource": DS, "gridPos": {"h": h, "w": w, "x": x, "y": y},
         "targets": [{"datasource": DS, "expr": e, "legendFormat": l, "refId": chr(65 + i)} for i, (e, l) in enumerate(targets)],
         "fieldConfig": {"defaults": {"unit": unit, "custom": {"lineWidth": 2, "fillOpacity": 15, "stacking": {"mode": "normal" if stack else "none"}},
                                      **({"max": maxv} if maxv is not None else {}), "noValue": "sin datos"}, "overrides": []},
         "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}}
    panels.append(p)


def stat(title, expr, unit, x, w=4, h=4, desc="", thresholds=None, mappings=None, legend=""):
    panels.append({"type": "stat", "title": title, "description": desc, "datasource": DS, "gridPos": {"h": h, "w": w, "x": x, "y": y},
                   "targets": [{"datasource": DS, "expr": expr, "legendFormat": legend, "refId": "A", "instant": True}],
                   "fieldConfig": {"defaults": {"unit": unit, "noValue": "sin datos", "mappings": mappings or [],
                                                "thresholds": {"mode": "absolute", "steps": thresholds or [{"color": "green", "value": None}]}}, "overrides": []},
                   "options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "background", "graphMode": "none", "textMode": "value_and_name"}})


def bar(title, expr, legend, x, w=8, h=8, desc="", unit="short"):
    panels.append({"type": "barchart", "title": title, "description": desc, "datasource": DS, "gridPos": {"h": h, "w": w, "x": x, "y": y},
                   "targets": [{"datasource": DS, "expr": expr, "legendFormat": legend, "refId": "A", "instant": True, "format": "table"}],
                   "transformations": [{"id": "reduce", "options": {"reducers": ["lastNotNull"], "mode": "seriesToRows"}}],
                   "fieldConfig": {"defaults": {"unit": unit, "noValue": "sin datos"}, "overrides": []},
                   "options": {"orientation": "horizontal", "showValue": "always", "legend": {"showLegend": False}}})


UPDOWN = [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}]
RG = [{"color": "red", "value": None}, {"color": "green", "value": 1}]

row("Estado")
stat("Alice API (scrape)", 'up{job="alice"}', "none", 0, mappings=UPDOWN, thresholds=RG)
stat("Ollama", 'alice_dependency_up{dependency="ollama"}', "none", 4, mappings=UPDOWN, thresholds=RG)
stat("Qdrant", 'alice_dependency_up{dependency="qdrant"}', "none", 8, mappings=UPDOWN, thresholds=RG)
stat("Prometheus", 'up{job="prometheus"}', "none", 12, mappings=UPDOWN, thresholds=RG)
stat("Grafana", 'up{job="grafana"}', "none", 16, mappings=UPDOWN, thresholds=RG)
stat("windows_exporter", 'up{job="windows"}', "none", 20, mappings=UPDOWN, thresholds=RG)
y += 4
stat("Docker", 'alice_dependency_up{dependency="docker"}', "none", 0, mappings=UPDOWN, thresholds=RG,
     desc="Docker no está instalado en Beta 0.1 (decisión D1: runtime nativo). DOWN es el estado real, no un fallo de Alice.")
stat("OpenRouter (última llamada)", 'alice_dependency_up{dependency="openrouter"}', "none", 4, mappings=UPDOWN, thresholds=RG,
     desc="1 solo tras una llamada real exitosa; no se hacen llamadas facturables como health check.")
stat("GPU muestreo", "alice_gpu_sample_success", "none", 8, mappings=UPDOWN, thresholds=RG, desc="nvidia-smi respondió en el último muestreo")
stat("Cola local", "alice_queue_depth", "short", 12, thresholds=[{"color": "green", "value": None}, {"color": "orange", "value": 2}, {"color": "red", "value": 4}])
stat("Coste cloud (rango)", "sum(increase(alice_provider_cost_usd_total[$__range]))", "currencyUSD", 16,
     desc="Solo importes reportados por el proveedor. Coste desconocido no se cuenta como cero: ver ledger en Alice.")
stat("Peticiones (rango)", "sum(increase(alice_requests_total[$__range]))", "short", 20)
y += 4

row("Host Windows (windows_exporter)")
ts("CPU del host", [('100 - avg(rate(windows_cpu_time_total{mode="idle"}[1m])) * 100', "CPU %")], "percent", 0, maxv=100,
   desc="Porcentaje del host completo (todos los núcleos). Fuente: windows_exporter.")
ts("RAM del host", [("windows_memory_physical_total_bytes - windows_memory_available_bytes", "usada"),
                    ("windows_memory_available_bytes", "disponible")], "bytes", 8, stack=True)
ts("Red y disco", [("sum(rate(windows_net_bytes_total[1m]))", "red B/s"),
                   ("sum(rate(windows_physical_disk_read_bytes_total[1m]))", "disco lectura B/s"),
                   ("sum(rate(windows_physical_disk_write_bytes_total[1m]))", "disco escritura B/s")], "Bps", 16)
y += 8

row("GPU (nvidia-smi vía Alice)")
ts("Utilización GPU", [("alice_gpu_utilization_percent", "GPU {{gpu}}")], "percent", 0, maxv=100)
ts("VRAM", [("alice_gpu_memory_used_bytes", "usada"), ("alice_gpu_memory_total_bytes", "total"),
            ("sum(alice_ollama_model_loaded_vram_bytes)", "modelos Ollama")], "bytes", 8)
ts("Temperatura y consumo", [("alice_gpu_temperature_celsius", "°C"), ("alice_gpu_power_watts", "W")], "none", 16)
y += 8

row("Alice: tráfico y routing")
ts("Peticiones por ruta", [("sum by (route) (rate(alice_requests_total[5m])) * 60", "{{route}}")], "reqpm", 0, stack=True)
bar("Distribución de rutas (rango)", "sum by (route) (increase(alice_requests_total[$__range]))", "{{route}}", 8)
bar("Local vs externo (rango)", 'sum by (provider) (increase(alice_requests_total{provider!="none"}[$__range]))', "{{provider}}", 16,
    desc="ollama/local-tools = local; openrouter/tavily = salida externa autorizada")
y += 8

row("Alice: latencia, errores, proveedores")
ts("Latencia end-to-end", [("histogram_quantile(0.5, sum by (le) (rate(alice_request_duration_seconds_bucket[5m])))", "p50"),
                           ("histogram_quantile(0.95, sum by (le) (rate(alice_request_duration_seconds_bucket[5m])))", "p95")], "s", 0,
   desc="p50/p95 calculados desde histogramas (no se promedian percentiles).")
ts("Etapas: cola, RAG, proveedor (p95)", [("histogram_quantile(0.95, sum by (le) (rate(alice_queue_wait_seconds_bucket[5m])))", "cola"),
                                          ("histogram_quantile(0.95, sum by (le) (rate(alice_rag_retrieval_duration_seconds_bucket[5m])))", "RAG"),
                                          ("histogram_quantile(0.95, sum by (le, provider) (rate(alice_provider_request_duration_seconds_bucket[5m])))", "{{provider}}")], "s", 8)
ts("Errores y bloqueos", [("sum by (component) (rate(alice_errors_total[5m])) * 60", "error {{component}}"),
                          ("sum by (reason) (rate(alice_egress_blocked_total[5m])) * 60", "egress bloqueado: {{reason}}")], "short", 16)
y += 8
ts("Tokens por proveedor", [("sum by (provider, direction) (rate(alice_provider_tokens_total[5m])) * 60", "{{provider}} {{direction}}")], "short", 0, w=12,
   desc="Tokens por minuto")
ts("Scrapes de Prometheus", [("up", "{{job}}")], "none", 12, w=12, maxv=1)
y += 8

dash = {"uid": "alice-overview", "title": "ALICE / OVERVIEW", "tags": ["alice"], "timezone": "browser", "schemaVersion": 39,
        "time": {"from": "now-30m", "to": "now"}, "refresh": "15s", "panels": panels, "editable": False,
        "templating": {"list": []}, "annotations": {"list": []}}
out = Path(__file__).parent / "dashboards" / "alice-overview.json"
out.write_text(json.dumps(dash, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"{len(panels)} panels -> {out}")
