"""
Meta Ad Library Social Signals Adapter.
Conforms to SourceAdapter Protocol.
Extracts active advertiser copywriting phrases, hook patterns, and promotional keywords.
High ToS risk; strictly stops at any login wall or security check.
Disabled by default unless SOURCES_ALLOW_HIGH_RISK=true.
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

logger = logging.getLogger("backend.scrapers.adapters.facebook_adlibrary")


class FacebookAdLibraryAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="facebook",
            group="Search and social",
            kind="social",
            roles=["signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[SocialSignal]:
        """Pure parser for Meta Ad Library listing HTML."""
        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        signals: list[SocialSignal] = []
        seen: set[str] = set()

        # Ad cards in Meta Ad Library
        cards = soup.select("div[data-testid='ad_card'], div._8n-")
        for card in cards[:20]:
            body_el = card.select_one("div._7jyr, div[style*='white-space: pre-wrap']")
            if not body_el:
                body_el = card

            text = body_el.get_text(separator=" ", strip=True)
            # Find phrases like '100% cotton', 'oversized tee', 'buy 2 get 1', 'free shipping'
            phrases = re.findall(r"([A-Za-z0-9\s-]{4,35})", text)
            for p in phrases:
                clean = p.lower().strip()
                if len(clean) >= 6 and clean not in seen and not clean.isdigit():
                    seen.add(clean)
                    signals.append(
                        SocialSignal(
                            source="facebook",
                            phrase=clean,
                            mentions=1,
                            samples=[clean],
                        )
                    )

        return signals

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("facebook")
        settings = get_settings()

        if not settings.SOURCES_ALLOW_HIGH_RISK and spec and not spec.default_enabled:
            return SourceResult(
                source_id="facebook",
                status="skipped",
                cause="login_wall",
                signals=[],
                note="Meta Ad Library is high risk and disabled (SOURCES_ALLOW_HIGH_RISK=false).",
            )

        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=IN&q={encoded}"

        context = await browser_mgr.get_context("facebook")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "facebook", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked or "login" in page.url or "checkpoint" in page.url:
                logger.info("Meta Ad Library login wall/checkpoint detected. Stopping politely.")
                return SourceResult(
                    source_id="facebook",
                    status="blocked",
                    cause="login_wall",
                    signals=[],
                    duration_ms=duration_ms,
                    note="Meta Ad Library login requirement encountered.",
                )

            signals = self.parse(content)
            status = "ok" if len(signals) >= 3 else ("partial" if signals else "error")

            return SourceResult(
                source_id="facebook",
                status=status,
                strategy_used="dom_selectors" if signals else None,
                signals=signals[:25],
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Meta Ad Library search failed: {e}")
            return SourceResult(
                source_id="facebook",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_facebook_signals = FacebookAdLibraryAdapter().parse
