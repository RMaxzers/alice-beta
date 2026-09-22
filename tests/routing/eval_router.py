"""Router evaluation against live Ollama (embeddings + classifier). Writes docs/ROUTER-EVAL.md.
Run: uv run python -m tests.routing.eval_router
"""
from __future__ import annotations

import asyncio
import statistics
import time
from collections import defaultdict
from pathlib import Path

import yaml

from apps.api.config import ROOT, load_yaml, settings
from packages.schemas.models import Privacy, Route
from services.providers.ollama import OllamaProvider
from services.router.router import Router, RouterContext


async def main() -> None:
    ol = OllamaProvider(settings().ollama_base_url)
    aliases = load_yaml("config/models/aliases.yaml")["aliases"]
    emb, cls = aliases["local-embedding"]["model"], aliases["local-classifier"]["model"]
    r = Router(embed=lambda t: ol.embed(emb, t),
               classify=lambda m, s: ol.complete_json(cls, m, s, {"temperature": 0, "num_ctx": 2048}))
    await r.warmup()
    cases = yaml.safe_load((ROOT / "tests/routing/cases.yaml").read_text(encoding="utf-8"))
    per = defaultdict(lambda: [0, 0])
    lat, rows, by = [], [], defaultdict(int)
    sets = defaultdict(lambda: [0, 0])
    for c in cases:
        ctx = RouterContext(privacy=Privacy.PRIVATE, attached_kinds=tuple(c.get("attached", [])))
        t0 = time.perf_counter()
        d, _ = await r.route(c["q"], ctx)
        dt = time.perf_counter() - t0
        lat.append(dt)
        ok = d.route == Route(c["route"])
        per[c["route"]][0] += ok
        per[c["route"]][1] += 1
        by[d.decided_by] += 1
        rows.append((c["q"], c["route"], d.route.value, d.decided_by, d.confidence, dt, ok))
        sets[c.get("set", "eval-1")][0] += ok
        sets[c.get("set", "eval-1")][1] += 1
    total_ok = sum(v[0] for v in per.values())
    acc = total_ok / len(cases)
    lat_sorted = sorted(lat)
    p95 = lat_sorted[max(0, int(len(lat) * 0.95) - 1)]
    out = [
        "# Router evaluation", "",
        f"Date: {time.strftime('%Y-%m-%d %H:%M')} · cases: {len(cases)} · embeddings: {emb} · classifier: {cls}", "",
        f"**Accuracy: {total_ok}/{len(cases)} = {acc:.1%}** · malformed classifier outputs: {r.stats['malformed']}",
        f"Latency: p50 {statistics.median(lat)*1000:.0f} ms · p95 {p95*1000:.0f} ms · max {max(lat)*1000:.0f} ms (includes embedding/classifier calls)",
        f"Decided by: {dict(by)}",
        "By set: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sets.items()) + " (holdout2 was written after eval-1 rule changes and never used for tuning)", "", "| Route | Correct |", "|---|---|",
        *[f"| {k} | {v[0]}/{v[1]} |" for k, v in sorted(per.items())], "",
        "| Query | Expected | Got | By | Conf. | ms | OK |", "|---|---|---|---|---|---|---|",
        *[f"| {q[:60]} | {e} | {g} | {b} | {'' if cf is None else f'{cf:.2f}'} | {dt*1000:.0f} | {'✅' if ok else '❌'} |"
          for q, e, g, b, cf, dt, ok in rows],
    ]
    Path(ROOT / "docs/ROUTER-EVAL.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:8]))


if __name__ == "__main__":
    asyncio.run(main())
