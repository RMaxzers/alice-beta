"""Cost ledger with atomic budget reservation. Unknown cost is recorded as unknown, never zero."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apps.api.db import tx


class BudgetExceeded(Exception):
    pass


class Ledger:
    def __init__(self, con: sqlite3.Connection, per_request_usd: float, daily_usd: float, tz: str):
        self.con, self.per_request, self.daily, self.tz = con, per_request_usd, daily_usd, ZoneInfo(tz)

    def _day_start_utc(self) -> str:
        local = datetime.now(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        return local.astimezone(timezone.utc).isoformat()

    def spent_today(self) -> dict:
        rows = self.con.execute(
            "SELECT state, COUNT(*) n, SUM(reserved_usd) r, SUM(COALESCE(reported_usd, estimated_usd)) c FROM ledger "
            "WHERE created_at >= ? GROUP BY state", (self._day_start_utc(),)).fetchall()
        out = {"reserved_open": 0.0, "accounted": 0.0, "unknown_cost_calls": 0, "calls": 0}
        for r in rows:
            out["calls"] += r["n"]
            if r["state"] == "reserved":
                out["reserved_open"] += r["r"] or 0
            elif r["state"] == "reconciled":
                out["accounted"] += r["c"] or 0
            elif r["state"] == "unknown_cost":
                out["unknown_cost_calls"] += r["n"]
                out["reserved_open"] += r["r"] or 0  # keep reservation as worst case
        return out

    def reserve(self, request_id: str, route: str, provider: str, model: str, max_cost: float | None) -> str:
        if max_cost is None:
            raise BudgetExceeded("No se puede estimar el coste máximo; llamada no permitida")
        if max_cost > self.per_request:
            raise BudgetExceeded(f"Coste máximo estimado USD {max_cost:.4f} supera el límite por petición USD {self.per_request:.2f}")
        aid = uuid.uuid4().hex
        with tx(self.con):
            s = self.spent_today()
            if s["accounted"] + s["reserved_open"] + max_cost > self.daily:
                raise BudgetExceeded(f"Presupuesto diario USD {self.daily:.2f} agotado")
            self.con.execute(
                "INSERT INTO ledger(attempt_id, request_id, created_at, route, provider, model, reserved_usd, estimated_usd, state)"
                " VALUES (?,?,?,?,?,?,?,?, 'reserved')",
                (aid, request_id, datetime.now(timezone.utc).isoformat(), route, provider, model, max_cost, max_cost))
        return aid

    def reconcile(self, attempt_id: str, tokens_in: int | None, tokens_out: int | None, reported_usd: float | None) -> None:
        state = "reconciled" if reported_usd is not None else "unknown_cost"
        with tx(self.con):
            self.con.execute("UPDATE ledger SET tokens_in=?, tokens_out=?, reported_usd=?, state=? WHERE attempt_id=?",
                             (tokens_in, tokens_out, reported_usd, state, attempt_id))

    def release(self, attempt_id: str) -> None:
        """Call failed before any tokens were billed."""
        with tx(self.con):
            self.con.execute("UPDATE ledger SET state='released' WHERE attempt_id=? AND state='reserved'", (attempt_id,))
