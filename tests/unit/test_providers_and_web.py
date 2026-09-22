from __future__ import annotations

import pytest

from apps.api.db import connect, migrate
from services.policies.egress import EgressDenied
from services.providers.ledger import BudgetExceeded, Ledger
from services.integrations.web import check_url


@pytest.mark.parametrize("url", ["http://127.0.0.1:9090/api/v1/query", "http://localhost:11434", "http://169.254.169.254/latest/meta-data",
                                 "http://10.0.0.5/", "http://192.168.1.1/", "file:///C:/Windows/win.ini", "ftp://example.org",
                                 "http://[::1]:6333/", "https://eva01.tail3f8e85.ts.net/", "http://user:pw@example.org/",
                                 "http://100.100.100.100/"])
def test_ssrf_blocked(url):
    with pytest.raises(EgressDenied):
        check_url(url)


@pytest.fixture
def ledger(tmp_path):
    con = connect(tmp_path / "l.db")
    migrate(con)
    return Ledger(con, per_request_usd=0.05, daily_usd=0.10, tz="America/Santiago")


def test_budget_reservation(ledger):
    with pytest.raises(BudgetExceeded, match="por petición"):
        ledger.reserve("r", "CLOUD", "openrouter", "m", 0.06)
    with pytest.raises(BudgetExceeded, match="estimar"):
        ledger.reserve("r", "CLOUD", "openrouter", "m", None)
    a = ledger.reserve("r1", "CLOUD", "openrouter", "m", 0.05)
    b = ledger.reserve("r2", "CLOUD", "openrouter", "m", 0.05)
    with pytest.raises(BudgetExceeded, match="diario"):
        ledger.reserve("r3", "CLOUD", "openrouter", "m", 0.01)   # open reservations count against the day
    ledger.release(a)
    ledger.reconcile(b, 10, 5, None)                              # unknown cost: not zero
    s = ledger.spent_today()
    assert s["unknown_cost_calls"] == 1 and s["reserved_open"] == pytest.approx(0.05)


async def test_ollama_provider_normalizes_connection_errors(egress):
    from services.providers.base import ProviderError
    from services.providers.ollama import OllamaProvider
    with pytest.raises(ProviderError, match="ollama_unavailable"):
        async for _ in OllamaProvider("http://127.0.0.1:11434").stream("m", [], {}):
            pass
    assert (await OllamaProvider("http://127.0.0.1:11434").health()).state == "unavailable"


async def test_openrouter_health_never_bills(egress):
    from services.providers.openrouter import OpenRouterProvider
    assert (await OpenRouterProvider("").health()).state == "not_configured"
    assert (await OpenRouterProvider("k").health()).state == "configured_not_tested"
    assert egress.requests == []
