"""Shared fixtures. The `egress` fixture routes ALL httpx traffic through a recorder so tests can prove
whether any content left the host (POST to a non-loopback host = content egress)."""
from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx
import pytest

from apps.api.config import Settings

_RealAsyncClient = httpx.AsyncClient
LOCAL_HOSTS = {"127.0.0.1", "localhost"}

CATALOG = {"data": [
    {"id": "anthropic/claude-sonnet-5", "pricing": {"prompt": "0.000002", "completion": "0.00001"}, "context_length": 1000000},
    {"id": "deepseek/deepseek-v4.1-flash", "pricing": {"prompt": "0.00000015", "completion": "0.0000006"}, "context_length": 1000000},
]}
SSE = ('data: {"choices":[{"delta":{"content":"respuesta cloud"}}]}\n\n'
       'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":3,"cost":0.0001}}\n\ndata: [DONE]\n\n')


class Recorder:
    def __init__(self):
        self.requests: list[tuple[str, str, str]] = []
        self.ollama_up = False

    @property
    def content_egress(self) -> list[tuple[str, str, str]]:
        return [r for r in self.requests if r[0] == "POST" and urlparse(r[1]).hostname not in LOCAL_HOSTS]

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = request.content.decode(errors="replace") if request.content else ""
        self.requests.append((request.method, str(request.url), body))
        host, path = request.url.host, request.url.path
        if host in LOCAL_HOSTS:
            if not self.ollama_up:
                raise httpx.ConnectError("simulated: local service down", request=request)
            if path == "/api/chat":
                return httpx.Response(200, content=b'{"message":{"content":"local"},"done":false}\n{"done":true,"eval_count":1,"prompt_eval_count":1}\n')
            if path == "/api/embed":
                n = len(json.loads(body)["input"])
                return httpx.Response(200, json={"embeddings": [[0.1] * 8] * n})
            return httpx.Response(200, json={})
        if host == "openrouter.ai" and path.endswith("/models"):
            return httpx.Response(200, json=CATALOG)
        if host == "openrouter.ai" and path.endswith("/chat/completions"):
            return httpx.Response(200, content=SSE.encode(), headers={"content-type": "text/event-stream"})
        if host == "api.tavily.com":
            return httpx.Response(200, json={"results": [{"title": "t", "url": "https://example.org", "content": "c"}]})
        return httpx.Response(404)


@pytest.fixture
def egress(monkeypatch):
    rec = Recorder()

    def factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(*args, transport=httpx.MockTransport(rec.handler), **kwargs)
    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return rec


@pytest.fixture
def settings_tmp(tmp_path):
    return Settings(_env_file=None, alice_session_secret="s" * 64, alice_password="pw", openrouter_api_key="sk-test",
                    tavily_api_key="tv-test", storage_dir=tmp_path / "storage", data_dir=tmp_path / "data", logs_dir=tmp_path / "logs",
                    alice_cloud_enabled=True, alice_local_only=False)


@pytest.fixture
def state(settings_tmp, egress):
    from apps.api.state import AliceState
    return AliceState(settings_tmp)


async def collect(agen) -> list[dict]:
    return [e async for e in agen]
