from __future__ import annotations

import json
import time
from typing import AsyncIterator

import httpx

from packages.schemas.models import Privacy
from services.policies.egress import Clearance, EgressDenied
from services.providers.base import Chunk, Health, ProviderError, Usage

API = "https://openrouter.ai/api/v1"


def request_payload(model: str, messages: list[dict]) -> dict:
    """The exact content that leaves the host; hashed for authorization."""
    return {"model": model, "messages": messages}


class OpenRouterProvider:
    name = "openrouter"
    local = False

    def __init__(self, api_key: str, timeout: float = 60.0):
        self._key = api_key
        self.timeout = timeout
        self._catalog: dict[str, dict] = {}
        self._catalog_at = 0.0
        self.last_test: Health | None = None

    @property
    def configured(self) -> bool:
        return bool(self._key)

    async def health(self) -> Health:
        # No billable calls as health checks: report config + result of the last real call.
        if not self.configured:
            return Health("not_configured", "OPENROUTER_API_KEY ausente")
        return self.last_test or Health("configured_not_tested", "Clave presente; sin llamada real todavía")

    async def pricing(self, model: str) -> dict | None:
        """USD per token from the public catalog (no content sent). Cached 1h."""
        if time.time() - self._catalog_at > 3600:
            async with httpx.AsyncClient(timeout=10) as c:
                data = (await c.get(f"{API}/models")).json()["data"]
            self._catalog = {m["id"]: m for m in data}
            self._catalog_at = time.time()
        m = self._catalog.get(model)
        if not m:
            return None
        p = m.get("pricing", {})
        return {"prompt": float(p.get("prompt", 0)), "completion": float(p.get("completion", 0)),
                "context_length": m.get("context_length")}

    async def estimate_max_cost(self, model: str, messages: list[dict], max_tokens: int) -> float | None:
        p = await self.pricing(model)
        if p is None:
            return None
        chars = sum(len(m.get("content", "")) for m in messages)
        tokens_in = chars // 3 + 50  # conservative upper-bound heuristic (≈3 chars/token)
        return tokens_in * p["prompt"] + max_tokens * p["completion"]

    async def stream(self, model: str, messages: list[dict], options: dict, clearance: Clearance | None = None) -> AsyncIterator[Chunk]:
        if clearance is None:
            raise EgressDenied("no_clearance", "OpenRouter requires an EgressGate clearance")
        clearance.verify(self.name, model, request_payload(model, messages))
        if not self.configured:
            raise ProviderError("not_configured", "OPENROUTER_API_KEY ausente")
        body = {
            **request_payload(model, messages),
            "stream": True,
            "max_tokens": int(options.get("max_tokens", 1500)),
            "usage": {"include": True},
            # Never let OpenRouter re-route to a different provider/model than the one authorized.
            "provider": {"allow_fallbacks": False,
                         "data_collection": "allow" if clearance.privacy == Privacy.PUBLIC else "deny"},
        }
        headers = {"Authorization": f"Bearer {self._key}", "X-Title": "Alice Beta"}
        usage = Usage()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10)) as c:
                async with c.stream("POST", f"{API}/chat/completions", json=body, headers=headers) as r:
                    if r.status_code != 200:
                        txt = (await r.aread()).decode(errors="replace")[:300]
                        self.last_test = Health("degraded", f"HTTP {r.status_code}")
                        raise ProviderError(f"http_{r.status_code}", txt, retryable=r.status_code in (429, 502, 503))
                    async for line in r.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        d = json.loads(data)
                        if "error" in d:
                            raise ProviderError("provider_error", str(d["error"])[:300])
                        if d.get("usage"):
                            u = d["usage"]
                            usage = Usage(u.get("prompt_tokens"), u.get("completion_tokens"), u.get("cost"))
                        for ch in d.get("choices", []):
                            t = (ch.get("delta") or {}).get("content")
                            if t:
                                yield Chunk(text=t)
            self.last_test = Health("healthy", f"última llamada OK ({model})")
            yield Chunk(done=True, usage=usage)
        except httpx.HTTPError as e:
            self.last_test = Health("unavailable", type(e).__name__)
            raise ProviderError("network", type(e).__name__, retryable=True) from e
