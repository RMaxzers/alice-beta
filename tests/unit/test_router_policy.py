from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from apps.api.config import ROOT
from packages.schemas.models import Privacy, Route, RouteDecision
from services.router.router import Router, RouterContext


async def _route(text, **ctx):
    r = Router(embed=None, classify=None)
    return (await r.route(text, RouterContext(privacy=Privacy.PRIVATE, **ctx)))[0]


@pytest.mark.parametrize("q,route", [
    ("¿Cómo está Alice?", Route.OBSERVABILITY), ("¿Qué contenedor consume más RAM?", Route.OBSERVABILITY),
    ("Escribe un PowerShell que muestre los cinco procesos que más CPU consumen.", Route.LOCAL_CODE),
    ("Investiga las novedades recientes de Ollama.", Route.WEB_RESEARCH),
    ("¿Cuántos activos del inventario están fuera de soporte?", Route.STRUCTURED_QUERY),
])
async def test_rules(q, route):
    assert (await _route(q)).route == route


async def test_attachments_take_precedence():
    assert (await _route("usa el modelo cloud", attached_kinds=("pdf",))).route == Route.LOCAL_RAG
    assert (await _route("hola", attached_kinds=("csv",))).route == Route.STRUCTURED_QUERY
    assert (await _route("hola", attached_kinds=("log",))).route == Route.LOG_ANALYSIS


async def test_unavailable_cloud_is_downgraded_to_local_with_reason():
    d = await _route("Investiga las novedades recientes de Ollama.", cloud_available=False)
    assert d.route == Route.LOCAL_SIMPLE and d.decided_by == "policy" and "no disponible" in d.reason


async def test_malformed_classifier_output_falls_back_safely():
    async def bad(msgs, schema):
        return '{"route": "DELETE_EVERYTHING", "confidence": 7}'
    r = Router(embed=None, classify=bad)
    d, _ = await r.route("texto ambiguo sin reglas", RouterContext(privacy=Privacy.PRIVATE))
    assert d.route == Route.LOCAL_SIMPLE and r.stats["malformed"] == 1


def test_decision_schema_is_strict():
    with pytest.raises(ValidationError):
        RouteDecision(category="x", complexity="low", privacy="PRIVATE", requires_web=False, requires_rag=False,
                      requires_tools=False, route="LOCAL_SIMPLE", decided_by="rules", reason="r", evil=True)
    with pytest.raises(ValidationError):
        RouteDecision(category="x", complexity="low", privacy="PRIVATE", requires_web=False, requires_rag=False,
                      requires_tools=False, route="NOT_A_ROUTE", decided_by="rules", reason="r")


def test_eval_set_has_30_plus_cases_covering_routes():
    cases = yaml.safe_load((ROOT / "tests/routing/cases.yaml").read_text(encoding="utf-8"))
    assert len(cases) >= 30
    assert {c["route"] for c in cases} >= {"LOCAL_SIMPLE", "LOCAL_CODE", "LOCAL_RAG", "WEB_RESEARCH", "FINANCIAL_RESEARCH",
                                          "OBSERVABILITY", "AUTOMATION", "CLOUD_POWERFUL"}
    exemplars = yaml.safe_load((ROOT / "config/routing/exemplars.yaml").read_text(encoding="utf-8"))
    tuning = {t for v in exemplars.values() for t in v}
    assert not tuning & {c["q"] for c in cases}, "evaluation cases leaked into tuning exemplars"
