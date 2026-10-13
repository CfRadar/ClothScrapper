"""
IndiaMART B2B Source Adapter.
Conforms to SourceAdapter Protocol.
Extracts wholesale product cards with supplier, location, MOQ, and unit price information.
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

logger = logging.getLogger("backend.scrapers.adapters.indiamart")


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


class IndiamartAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="indiamart",
            group="B2B",
            kind="b2b",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """Pure parser function extracting B2B items from IndiaMART search directory HTML."""
        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select(".card, .product-card, .listing-card, div[data-click='productTitle']")
        if not cards:
            cards = soup.select("div.m-lst, div.g-c, div.s-card")

        items: list[Item] = []

        for idx, card in enumerate(cards[:40], 1):
            title_el = (
                card.select_one(".product-title, .title, .m-pn, h2, a[data-click='productTitle']")
                or card.select_one("a.cardlinks")
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title or len(title) < 4:
                continue

            price_el = card.select_one(".price, .prc, .price-range, span.prc-val")
            price_text = price_el.get_text(strip=True) if price_el else ""
            price_val = parse_price(price_text)

            # Supplier name
            supplier_el = card.select_one(".company-name, .co-nm, .seller-name, .comp-nm, a.company-name")
            supplier = supplier_el.get_text(strip=True) if supplier_el else None

            # Location / City
            loc_el = card.select_one(".location, .city, .loc, .comp-city, span.c-city")
            location = loc_el.get_text(strip=True) if loc_el else None

            # MOQ (Minimum Order Quantity)
            moq_el = card.select_one(".moq, .min-order, span.qnty, .order-qty")
            moq = moq_el.get_text(strip=True) if moq_el else None

            # Unit
            unit_el = card.select_one(".price-unit, .unit, span.unit-val")
            unit = unit_el.get_text(strip=True) if unit_el else None

            # Truststamp / Verified
            verified = bool(card.select_one(".truststamp, .verified, .verified-seller, .ts-icon"))

            link_el = card.select_one("a[href]")
            href = link_el.get("href", "") if link_el else ""
            full_url = urllib.parse.urljoin("https://dir.indiamart.com", href)

            b2b_info = B2BInfo(
                supplier=supplier,
                location=location,
                moq=moq,
                unit=unit,
                price_range=price_text if not price_val else None,
                verified=verified,
            )

            items.append(
                Item(
                    source_id="indiamart",
                    title=title,
                    price=price_val,
                    position=idx,
                    url=full_url,
                    b2b=b2b_info,
                )
            )

        if not items:
            spec = get_source_spec("indiamart")
            items = parse_dom(raw, spec=spec, source_id="indiamart")

        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("indiamart")
        settings = get_settings()
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        encoded = urllib.parse.quote_plus(query)
        url = f"https://dir.indiamart.com/search.mp?ss={encoded}"

        context = await browser_mgr.get_context("indiamart")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "indiamart", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="indiamart",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="IndiaMART bot challenge triggered.",
                )

            items = self.parse(content)[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="indiamart",
                status=status,
                strategy_used="dom_selectors" if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"IndiaMART search failed: {e}")
            return SourceResult(
                source_id="indiamart",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = IndiamartAdapter().parse
