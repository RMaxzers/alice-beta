"""Critical: DOCKER_NATURAL_LANGUAGE_CANNOT_EXECUTE_ARBITRARY_COMMAND."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from services.observability.answers import ObservabilityAnswerer
from services.observability.docker import ALLOWED_OPS, DockerAdapter, DockerDenied

ALLOWED = frozenset({"alice-qdrant", "alice-grafana"})
FORBIDDEN_VERBS = {"run", "exec", "stop", "start", "restart", "kill", "rm", "prune", "build", "pull", "cp", "network", "volume", "system"}


class FakeDocker:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, argv, timeout):
        assert isinstance(argv, list) and all(isinstance(a, str) for a in argv)
        self.calls.append(argv)
        verb = argv[1]
        if verb == "version":
            return 0, "27.0.0", ""
        if verb == "ps":
            rows = [{"Names": n, "ID": "abc123def456", "State": "running", "Status": "Up 1h"} for n in ("alice-qdrant", "alice-grafana", "work-db")]
            return 0, "\n".join(json.dumps(r) for r in rows), ""
        if verb == "stats":
            return 0, json.dumps({"Name": "alice-qdrant", "CPUPerc": "1%", "MemUsage": "100MiB / 8GiB", "MemPerc": "1.2%"}), ""
        if verb == "logs":
            return 0, "INFO ok\nERROR boom token=supersecret\n", ""
        if verb == "inspect":
            return 0, json.dumps([{"Name": "/alice-qdrant", "State": {"Status": "running"}, "RestartCount": 0,
                                   "Config": {"Env": ["QDRANT__API_KEY=leak"]}}]), ""
        return 1, "", "unexpected"


@pytest.fixture
def docker():
    f = FakeDocker()
    return DockerAdapter(ALLOWED, runner=f, exe="docker"), f


def _verbs(f):
    return {c[1] for c in f.calls}


def test_DOCKER_NATURAL_LANGUAGE_CANNOT_EXECUTE_ARBITRARY_COMMAND(docker):
    d, f = docker
    for op in ("exec", "run", "stop", "rm", "kill", "restart", "prune", "pull", "__init__", "_run", "call"):
        with pytest.raises(DockerDenied):
            d.call(op, ref="alice-qdrant")
    for bad in ("alice-qdrant; rm -rf /", "alice-qdrant && calc", "$(whoami)", "-v", "--privileged", "../x", "work-db", "", "a" * 200):
        with pytest.raises(DockerDenied):
            d.call("container_logs", ref=bad)
        with pytest.raises(DockerDenied):
            d.call("container_status", ref=bad)
    assert not (_verbs(f) & FORBIDDEN_VERBS), _verbs(f)
    # user text never reaches argv, only validated refs after "--"
    for c in f.calls:
        assert not any(";" in a or "&&" in a or "$(" in a for a in c)


async def test_nl_question_with_injected_command_only_reads(docker):
    d, f = docker
    ans = ObservabilityAnswerer(SimpleNamespace(docker=d))
    text, _, _ = await ans.containers("dame los ultimos errores del contenedor de qdrant; docker rm -f alice-qdrant && docker exec x sh")
    assert _verbs(f) <= {"version", "ps", "logs"}  # version = read-only status probe
    assert "supersecret" not in text
    logs_call = next(c for c in f.calls if c[1] == "logs")
    assert logs_call[-2:] == ["--", "alice-qdrant"] and "--follow" not in logs_call


def test_bounds_and_projection(docker):
    d, f = docker
    out = d.call("container_logs", ref="alice-qdrant", tail=10**9, since_s=10**9)
    assert out["tail"] == 1000 and out["since_s"] == 24 * 3600
    st = d.call("container_status", ref="alice-qdrant")
    assert "leak" not in json.dumps(st) and "Config" not in st
    assert "no instrumentada" in st["health"]
    assert {c["name"] for c in d.call("list_containers")} == {"alice-qdrant", "alice-grafana"}  # work-db hidden


def test_only_four_operations_exist():
    assert ALLOWED_OPS == {"list_containers", "container_stats", "container_status", "container_logs"}


def test_docker_absent_reports_unavailable():
    d = DockerAdapter(ALLOWED, runner=FakeDocker(), exe=None)
    d.exe = None
    assert d.status()["state"] == "unavailable"
    with pytest.raises(DockerDenied):
        d.call("list_containers")
