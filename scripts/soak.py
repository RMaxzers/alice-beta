"""Sustained representative load (default 30 min): mixed local requests every ~20 s, samples RAM/VRAM/temp,
records latencies/errors, and checks for unexpected resets (Kernel-Power 41) / GPU TDR events. Writes docs/SOAK-REPORT.md.
Not a stress test: one request at a time, like a real demo session.
"""
from __future__ import annotations

import statistics
import subprocess
import sys
import time
from datetime import datetime

import httpx

from apps.api.config import ROOT
from scripts.alice_client import Client

MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 30
MIX = [("Explica brevemente qué es un balanceador de carga.", None, None),
       ("¿Cuántos activos del inventario están fuera de soporte?", None, None),
       ("¿Cuáles son los hallazgos principales?", "informe-auditoria-red-DEMO.pdf", None),
       ("¿Cómo está Alice?", None, None),
       ("Escribe una función en Python que calcule el promedio móvil de una lista.", None, None),
       ("Escribe unas 300 palabras sobre buenas prácticas de respaldo.", None, "LOCAL_SIMPLE")]


def sample() -> dict:
    out = {}
    try:
        g = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5).stdout.split(",")
        out.update(vram_mib=float(g[0]), gpu_util=float(g[1]), gpu_temp=float(g[2]))
    except Exception:  # noqa: BLE001
        pass
    try:
        r = httpx.get("http://127.0.0.1:9090/api/v1/query", params={"query": "windows_memory_available_bytes"}, timeout=5).json()
        out["ram_avail_gib"] = float(r["data"]["result"][0]["value"][1]) / 1024 ** 3
    except Exception:  # noqa: BLE001
        pass
    return out


def win_events(since: datetime) -> str:
    ps = ("$s=[datetime]'" + since.strftime("%Y-%m-%dT%H:%M:%S") + "'; "
          "@(Get-WinEvent -FilterHashtable @{LogName='System';StartTime=$s} -ErrorAction SilentlyContinue | "
          "Where-Object { $_.Id -eq 41 -or $_.Id -eq 4101 -or $_.ProviderName -match 'WHEA|nvlddmkm' }).Count")
    return subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout.strip()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    start = datetime.now()
    c = Client()
    docs = {d["original_name"]: d["document_id"] for d in c.get("/api/documents")}
    lat, errs, samples, n = [], [], [], 0
    end = time.time() + MINUTES * 60
    while time.time() < end:
        q, doc, route = MIX[n % len(MIX)]
        t0 = time.perf_counter()
        try:
            ev = c.chat(q, document_ids=[docs[doc]] if doc else None, force_route=route)
            if any(e["type"] == "error" for e in ev):
                errs.append(next(e["code"] for e in ev if e["type"] == "error"))
            lat.append(time.perf_counter() - t0)
        except Exception as e:  # noqa: BLE001
            errs.append(type(e).__name__)
        samples.append(sample())
        n += 1
        time.sleep(max(0, 20 - (time.perf_counter() - t0)))
    ev_count = win_events(start)
    ram = [s["ram_avail_gib"] for s in samples if "ram_avail_gib" in s]
    vram = [s["vram_mib"] for s in samples if "vram_mib" in s]
    temp = [s["gpu_temp"] for s in samples if "gpu_temp" in s]
    lat_s = sorted(lat)
    rep = [f"# Soak test — {start.strftime('%Y-%m-%d %H:%M')} → {datetime.now().strftime('%H:%M')} ({MINUTES:.0f} min)", "",
           f"- Requests: {n} (mixed local chat, SQL, RAG, observability, code, long generation; 1 at a time every ~20 s)",
           f"- Errors: {len(errs)} {errs[:10] if errs else ''}",
           f"- Latency: p50 {statistics.median(lat_s):.2f} s · p95 {lat_s[max(0, int(len(lat_s) * .95) - 1)]:.2f} s · max {max(lat_s):.2f} s" if lat_s else "- Latency: no data",
           f"- RAM available: min {min(ram):.1f} GiB · avg {statistics.mean(ram):.1f} GiB (target ≥ 2 GiB)" if ram else "- RAM: no data",
           f"- VRAM used: min {min(vram):.0f} · max {max(vram):.0f} MiB of 8192" if vram else "- VRAM: no data",
           f"- GPU temperature: max {max(temp):.0f} °C" if temp else "- GPU temp: no data",
           f"- Unexpected reset / TDR / WHEA events since start (Kernel-Power 41, nvlddmkm 4101, WHEA): **{ev_count}**", ""]
    (ROOT / "docs" / "SOAK-REPORT.md").write_text("\n".join(rep), encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
