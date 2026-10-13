"""
Snapmint Source Adapter.
Conforms to SourceAdapter Protocol.
Status: Unavailable (EMI payment platform without public product search).
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult

logger = logging.getLogger("backend.scrapers.adapters.snapmint")


class SnapmintAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="snapmint",
            group="B2C",
            kind="marketplace",
            roles=["sell_target"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        return []

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        return SourceResult(
            source_id="snapmint",
            status="unavailable",
            cause="wrong_url",
            items=[],
            note="EMI payment platform without public product search.",
        )
