from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Literal, Protocol

HealthState = Literal["not_configured", "configured_not_tested", "healthy", "degraded", "unavailable", "disabled"]


class ProviderError(Exception):
    def __init__(self, code: str, detail: str, retryable: bool = False):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.retryable = code, detail, retryable


@dataclass
class Usage:
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None  # reported by provider; None = unknown (never 0 by default)


@dataclass
class Chunk:
    text: str = ""
    done: bool = False
    usage: Usage = field(default_factory=Usage)


@dataclass
class Health:
    state: HealthState
    detail: str = ""


class ProviderAdapter(Protocol):
    name: str
    local: bool

    async def health(self) -> Health: ...

    def stream(self, model: str, messages: list[dict], options: dict, clearance=None) -> AsyncIterator[Chunk]: ...
