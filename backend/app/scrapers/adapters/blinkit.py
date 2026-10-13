"""
Blinkit Quick Commerce Source Adapter.
Conforms to SourceAdapter Protocol.
Requires DELIVERY_PINCODE for service availability.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any
from bs4 import BeautifulSoup

from backend.app.config import get_settings
from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec
from backend.app.scrapers.strategies.dom_selectors import parse_dom
from backend.app.scrapers.strategies.embedded_json import extract_embedded_json

logger = logging.getLogger("backend.scrapers.adapters.blinkit")


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", text)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


class BlinkitAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="blinkit",
            group="Quick commerce",
            kind="quickcommerce",
            roles=["sell_target"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """Pure parser for Blinkit catalog items."""
        if not isinstance(raw, str):
            return []

        # 1. Embedded JSON (__NEXT_DATA__)
        items = extract_embedded_json("blinkit", raw)
        if items:
            return items

        # 2. DOM parsing
        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("[data-test-id='plp-product-card'], div.product-card, div[role='button']")
        parsed_items: list[Item] = []

        for idx, card in enumerate(cards[:30], 1):
            title_el = card.select_one(".product-name, h2, .tw-line-clamp-2, div.title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 3:
                continue

            price_el = card.select_one(".product-price, span.price, div[data-test-id='price']")
            price_val = parse_price(price_el.get_text(strip=True) if price_el else None)

            link_el = card.select_one("a[href]")
            href = link_el.get("href", "") if link_el else ""
            full_url = urllib.parse.urljoin("https://blinkit.com", href)

            parsed_items.append(
                Item(
                    source_id="blinkit",
                    title=title,
                    price=price_val,
                    position=idx,
                    url=full_url,
                )
            )

        if not parsed_items:
            spec = get_source_spec("blinkit")
            parsed_items = parse_dom(raw, spec=spec, source_id="blinkit")

        return parsed_items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("blinkit")
        settings = get_settings()

        pincode = (settings.DELIVERY_PINCODE or "").strip()
        if not re.match(r"^\d{6}$", pincode):
            return SourceResult(
                source_id="blinkit",
                status="needs_location",
                cause="consent_or_location_modal",
                items=[],
                note="Blinkit requires a valid 6-digit DELIVERY_PINCODE in backend/.env.",
            )

        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
        encoded = urllib.parse.quote_plus(query)
        url = f"https://blinkit.com/s/?q={encoded}"

        context = await browser_mgr.get_context("blinkit")
        page = await context.new_page()

        try:
            # First set pincode if location prompt appears
            if spec:
                await browser_mgr.set_pincode(page, pincode, spec)

            is_blocked, content = await browser_mgr.polite_goto(page, url, "blinkit", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="blinkit",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="Blinkit bot challenge encountered.",
                )

            items = self.parse(content)[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="blinkit",
                status=status,
                strategy_used="dom_selectors" if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Blinkit search failed: {e}")
            return SourceResult(
                source_id="blinkit",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = BlinkitAdapter().parse
