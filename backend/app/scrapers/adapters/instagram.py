"""
Instagram Best-Effort Social Signal Adapter.
Conforms to SourceAdapter Protocol.
Disabled by default; respects login walls immediately.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.config import get_settings
from backend.app.scrapers.base import BaseSourceAdapter, Item, SocialSignal, SourceResult

logger = logging.getLogger("backend.scrapers.adapters.instagram")


class InstagramAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="instagram",
            group="Search and social",
            kind="social",
            roles=["signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        return []

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        settings = get_settings()
        if not settings.ENABLE_INSTAGRAM:
            return SourceResult(
                source_id="instagram",
                status="skipped",
                cause="login_wall",
                signals=[],
                note="Instagram adapter disabled by default (ENABLE_INSTAGRAM=false). Requires login.",
            )

        return SourceResult(
            source_id="instagram",
            status="blocked",
            cause="login_wall",
            signals=[],
            note="Instagram login wall encountered. Stopping politely.",
        )


scrape_instagram_best_effort = InstagramAdapter().search
