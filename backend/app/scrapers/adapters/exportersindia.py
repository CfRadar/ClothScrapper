"""
ExportersIndia B2B Source Adapter.
Conforms to SourceAdapter Protocol.
Extracts wholesale manufacturing listings with supplier, location, and MOQ info.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from typing import Any
from bs4 import BeautifulSoup

from backend.app.config import get_settings
from backend.app.scrapers.base import B2BInfo, BaseSourceAdapter, Item, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec
from backend.app.scrapers.strategies.dom_selectors import parse_dom

logger = logging.getLogger("backend.scrapers.adapters.exportersindia")


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(?:₹|Rs\.?)\s*([\d,]+(?:\.\d+)?)", text)
    if match:
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


class ExportersIndiaAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="exportersindia",
            group="B2B",
            kind="b2b",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """Pure parser for ExportersIndia listing HTML."""
        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select(".listing-item, .item, .pro-lst, div.ei-card")
        if not cards:
            cards = soup.select("div.classified-item, div.search-result")

        items: list[Item] = []

        for idx, card in enumerate(cards[:40], 1):
            title_el = card.select_one("h2, h3, a.title, .pro-title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 4:
                continue

            price_el = card.select_one(".price, .price-box, span.rate")
            price_text = price_el.get_text(strip=True) if price_el else ""
            price_val = parse_price(price_text)

            supplier_el = card.select_one(".company-name, .c-name, a.company, .comp-name")
            supplier = supplier_el.get_text(strip=True) if supplier_el else None

            location_el = card.select_one(".city, .location, span.address, .country-name")
            location = location_el.get_text(strip=True) if location_el else None

            moq_el = card.select_one(".moq, .min-order, span.quantity")
            moq = moq_el.get_text(strip=True) if moq_el else None

            link_el = card.select_one("a[href]")
            href = link_el.get("href", "") if link_el else ""
            full_url = urllib.parse.urljoin("https://www.exportersindia.com", href)

            b2b_info = B2BInfo(
                supplier=supplier,
                location=location,
                moq=moq,
                price_range=price_text if not price_val else None,
            )

            items.append(
                Item(
                    source_id="exportersindia",
                    title=title,
                    price=price_val,
                    position=idx,
                    url=full_url,
                    b2b=b2b_info,
                )
            )

        if not items:
            spec = get_source_spec("exportersindia")
            items = parse_dom(raw, spec=spec, source_id="exportersindia")

        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("exportersindia")
        settings = get_settings()
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.exportersindia.com/search.htm?q={encoded}"

        context = await browser_mgr.get_context("exportersindia")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "exportersindia", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="exportersindia",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="ExportersIndia bot check triggered.",
                )

            items = self.parse(content)[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="exportersindia",
                status=status,
                strategy_used="dom_selectors" if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"ExportersIndia search failed: {e}")
            return SourceResult(
                source_id="exportersindia",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = ExportersIndiaAdapter().parse
