"""Small authenticated client for demos/tests. Reads credentials from .env; never prints them.
Usage: uv run python -m scripts.alice_client "pregunta" [--privacy PUBLIC] [--doc ID] [--route LOCAL_SIMPLE]
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx

from apps.api.config import settings

BASE = "http://127.0.0.1:8000"


class Client:
    def __init__(self, base: str = BASE):
        s = settings()
        self.c = httpx.Client(base_url=base, timeout=300)
        r = self.c.post("/api/login", json={"username": s.alice_username, "password": s.alice_password.get_secret_value()})
        r.raise_for_status()
        self.csrf = r.json()["csrf"]
        self.h = {"x-csrf-token": self.csrf}

    def chat(self, message: str, privacy: str = "PRIVATE", document_ids=None, force_route=None, ticket=None, history=None) -> list[dict]:
        body = {"message": message, "privacy": privacy, "document_ids": document_ids or [], "history": history or []}
        if force_route:
            body["force_route"] = force_route
        if ticket:
            body["authorization_ticket"] = ticket
        events = []
        with self.c.stream("POST", "/api/chat", json=body, headers=self.h) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line.strip():
                    events.append(json.loads(line))
        return events

    def approve(self, ticket: str) -> dict:
        r = self.c.post(f"/api/egress/{ticket}/approve", headers=self.h)
        r.raise_for_status()
        return r.json()

    def upload(self, path: str, privacy: str = "PRIVATE") -> dict:
        with open(path, "rb") as f:
            r = self.c.post("/api/documents", files={"file": (path.replace("\\", "/").split("/")[-1], f)},
                            data={"privacy": privacy}, headers=self.h)
        r.raise_for_status()
        return r.json()

    def get(self, path: str, **params):
        r = self.c.get(path, params=params)
        r.raise_for_status()
        return r.json()


def render(events: list[dict]) -> str:
    out = []
    text = "".join(e["text"] for e in events if e["type"] == "token")
    for e in events:
        if e["type"] == "route":
            d = e["decision"]
            out.append(f"[route] {d['route']} by={d['decided_by']} alias={d['model_alias']} privacy={d['privacy']} conf={d['confidence']} — {d['reason']}")
        elif e["type"] == "tool":
            out.append(f"[tool] {e['name']}: {e['summary']}")
        elif e["type"] == "sources":
            for s in e["sources"]:
                out.append(f"[source] {s['kind']}: {s['title']} {s.get('location') or ''} {s.get('url') or ''}")
        elif e["type"] == "authorization_required":
            p = e["preview"]
            out.append(f"[AUTHORIZATION REQUIRED] provider={p['provider']} model={p['model']} privacy={p['privacy']} "
                       f"recipients={p['recipients']} fields={p['fields']} est_cost={p['estimated_cost_usd']} ticket={p['ticket_request_id']}")
        elif e["type"] == "error":
            out.append(f"[error] {e['code']}: {e['message']}")
        elif e["type"] == "done":
            out.append(f"[done] provider={e['provider']} model={e['model']} latency={e['latency_s']}s tokens_out={e['tokens_out']} "
                       f"cost={e['cost_usd']} ({e['cost_state']}) id={e['request_id']}")
    return "\n".join(out[:1] + [text] + out[1:])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("message")
    ap.add_argument("--privacy", default="PRIVATE")
    ap.add_argument("--doc", action="append")
    ap.add_argument("--route")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(render(Client().chat(a.message, a.privacy, a.doc, a.route)))
