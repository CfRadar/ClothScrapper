"""
Core data models and Protocol definition for Source Adapters.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

logger = logging.getLogger("backend.scrapers.base")


class B2BInfo(BaseModel):
    supplier: str | None = None
    location: str | None = None
    moq: str | None = None
    unit: str | None = None
    price_range: str | None = None
    verified: bool = False


class Item(BaseModel):
    source_id: str
    title: str
    brand: str | None = None
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int = 0
    sponsored: bool = False
    url: str | None = None
    b2b: B2BInfo | None = None

    @property
    def platform(self) -> str:
        return self.source_id


class SocialSignal(BaseModel):
    source: str
    phrase: str
    mentions: int = 1
    samples: list[str] = Field(default_factory=list)


class SourceResult(BaseModel):
    source_id: str
    status: Literal[
        "ok",
        "partial",
        "cached",
        "blocked",
        "unavailable",
        "needs_location",
        "error",
        "skipped",
    ]
    strategy_used: str | None = None
    cause: str | None = None
    items: list[Item] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    related_searches: list[str] = Field(default_factory=list)
    signals: list[SocialSignal] = Field(default_factory=list)
    duration_ms: int | float = 0
    note: str | None = None


@runtime_checkable
class SourceAdapter(Protocol):
    id: str
    group: str
    kind: str
    roles: list[str]

    async def search(self, query: str, ctx: Any) -> SourceResult: ...

    async def suggest(self, query: str, ctx: Any) -> list[str]: ...

    def parse(self, raw: str | dict[str, Any]) -> list[Item]: ...


class BaseSourceAdapter:
    """Base class for source adapters with default fallbacks."""

    def __init__(self, source_id: str, group: str, kind: str, roles: list[str]):
        self.id = source_id
        self.group = group
        self.kind = kind
        self.roles = roles

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        raise NotImplementedError("Adapters must implement pure parse method.")

    async def suggest(self, query: str, ctx: Any) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any) -> SourceResult:
        raise NotImplementedError("Adapters must implement async search method.")
