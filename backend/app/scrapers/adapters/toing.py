"""
Toing Quick Commerce Adapter Stub.
Conforms to SourceAdapter Protocol.
Status: Unavailable (Food delivery app without apparel catalog).
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult

logger = logging.getLogger("backend.scrapers.adapters.toing")


class ToingAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="toing",
            group="Quick commerce",
            kind="quickcommerce",
            roles=[],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        return []

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        return SourceResult(
            source_id="toing",
            status="unavailable",
            cause="wrong_url",
            items=[],
            note="Swiggy food delivery app, no apparel catalog.",
        )
