"""
Swiggy Instamart Quick Commerce Source Adapter.
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

logger = logging.getLogger("backend.scrapers.adapters.swiggy_instamart")


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


class SwiggyInstamartAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="swiggy_instamart",
            group="Quick commerce",
            kind="quickcommerce",
            roles=["sell_target"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """Pure parser for Swiggy Instamart products."""
        if not isinstance(raw, str):
            return []

        # 1. Embedded JSON
        items = extract_embedded_json("swiggy_instamart", raw)
        if items:
            return items

        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("[data-testid='default_container_item'], div.item-card, div._3w5_c")
        parsed_items: list[Item] = []

        for idx, card in enumerate(cards[:30], 1):
            title_el = card.select_one(".name, .item-name, h2, div[data-testid='item-name']")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 3:
                continue

            price_el = card.select_one(".price, span[data-testid='item-price'], span.rupee")
            price_val = parse_price(price_el.get_text(strip=True) if price_el else None)

            link_el = card.select_one("a[href]")
            href = link_el.get("href", "") if link_el else ""
            full_url = urllib.parse.urljoin("https://www.swiggy.com", href)

            parsed_items.append(
                Item(
                    source_id="swiggy_instamart",
                    title=title,
                    price=price_val,
                    position=idx,
                    url=full_url,
                )
            )

        if not parsed_items:
            spec = get_source_spec("swiggy_instamart")
            parsed_items = parse_dom(raw, spec=spec, source_id="swiggy_instamart")

        return parsed_items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("swiggy_instamart")
        settings = get_settings()

        pincode = (settings.DELIVERY_PINCODE or "").strip()
        if not re.match(r"^\d{6}$", pincode):
            return SourceResult(
                source_id="swiggy_instamart",
                status="needs_location",
                cause="consent_or_location_modal",
                items=[],
                note="Swiggy Instamart requires a valid 6-digit DELIVERY_PINCODE in backend/.env.",
            )

        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={encoded}"

        context = await browser_mgr.get_context("swiggy_instamart")
        page = await context.new_page()

        try:
            if spec:
                await browser_mgr.set_pincode(page, pincode, spec)

            is_blocked, content = await browser_mgr.polite_goto(page, url, "swiggy_instamart", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="swiggy_instamart",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="Swiggy Instamart bot challenge triggered.",
                )

            items = self.parse(content)[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="swiggy_instamart",
                status=status,
                strategy_used="dom_selectors" if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Swiggy Instamart search failed: {e}")
            return SourceResult(
                source_id="swiggy_instamart",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = SwiggyInstamartAdapter().parse
