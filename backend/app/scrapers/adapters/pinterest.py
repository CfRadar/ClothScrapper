"""
Pinterest Social Listening & Style Trends Adapter.
Conforms to SourceAdapter Protocol.
Extracts aesthetic fashion keywords, aesthetic styling phrases, and trend chips.
Stops politely upon encountering a login wall.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any
from bs4 import BeautifulSoup

from backend.app.config import get_settings
from backend.app.scrapers.base import BaseSourceAdapter, Item, SocialSignal, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec

logger = logging.getLogger("backend.scrapers.adapters.pinterest")


class PinterestAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="pinterest",
            group="Search and social",
            kind="social",
            roles=["signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[SocialSignal]:
        """Pure parser for Pinterest HTML pins and trend guide chips."""
        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        signals: list[SocialSignal] = []
        seen: set[str] = set()

        # 1. Search guide / trend suggestion chips
        guide_chips = soup.select("[data-test-id='search-guide'], div[role='listitem'] button")
        for chip in guide_chips:
            text = chip.get_text(strip=True).lower()
            if 3 <= len(text) <= 40 and text not in seen:
                seen.add(text)
                signals.append(
                    SocialSignal(
                        source="pinterest",
                        phrase=text,
                        mentions=2,
                        samples=["Search guide chip"],
                    )
                )

        # 2. Pin titles and descriptions
        pin_titles = soup.select("h2, h3, [data-test-id='pin-title'], div[data-test-id='visual-search-crop'] img")
        for el in pin_titles:
            text = ""
            if el.name == "img":
                text = el.get("alt", "").strip()
            else:
                text = el.get_text(strip=True)

            clean = re.sub(r"[^\w\s-]", "", text).lower().strip()
            if 5 <= len(clean) <= 60 and clean not in seen:
                seen.add(clean)
                signals.append(
                    SocialSignal(
                        source="pinterest",
                        phrase=clean,
                        mentions=1,
                        samples=[text[:70]],
                    )
                )

        return signals

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("pinterest")
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        encoded = urllib.parse.quote_plus(query)
        url = f"https://in.pinterest.com/search/pins/?q={encoded}"

        context = await browser_mgr.get_context("pinterest")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "pinterest", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            # Check if login wall blocked public view
            if is_blocked or "login" in page.url or "data-test-id=\"full-page-signup-modal\"" in content:
                logger.info("Pinterest login wall encountered. Stopping politely.")
                return SourceResult(
                    source_id="pinterest",
                    status="partial",
                    cause="login_wall",
                    signals=[],
                    duration_ms=duration_ms,
                    note="Pinterest login modal encountered. Best-effort signals returned.",
                )

            signals = self.parse(content)
            status = "ok" if len(signals) >= 3 else ("partial" if signals else "error")

            return SourceResult(
                source_id="pinterest",
                status=status,
                strategy_used="dom_selectors" if signals else None,
                signals=signals[:30],
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Pinterest search failed: {e}")
            return SourceResult(
                source_id="pinterest",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_pinterest_signals = PinterestAdapter().parse
