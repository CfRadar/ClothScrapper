"""
Myntra B2C Marketplace Source Adapter.
Conforms to SourceAdapter Protocol.
Strategy ladder:
2. Embedded JSON state: window.__myntraState
4. DOM selectors: li.product-base
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

logger = logging.getLogger("backend.scrapers.adapters.myntra")


class MyntraAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="myntra",
            group="B2C",
            kind="marketplace",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """
        Pure parser function. First attempts to extract structured embedded state
        window.__myntraState; falls back to DOM parsing.
        """
        if not isinstance(raw, str):
            return []

        # 1. Strategy 2: Embedded JSON state
        embedded_items = extract_embedded_json("myntra", raw)
        if embedded_items:
            return embedded_items

        # 2. Strategy 4: DOM parsing fallback
        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("li.product-base, div.product-card")
        items: list[Item] = []

        for idx, card in enumerate(cards, 1):
            brand_elem = card.select_one("h3.product-brand")
            name_elem = card.select_one("h4.product-product") or card.select_one("h3.product-brand + h4")
            brand = brand_elem.get_text(strip=True) if brand_elem else None
            name = name_elem.get_text(strip=True) if name_elem else ""
            title = f"{brand or ''} {name}".strip()
            if not title:
                continue

            price_elem = card.select_one("div.product-price span.product-discountedPrice") or card.select_one("div.product-price span")
            price_val = None
            if price_elem:
                raw_p = "".join(filter(lambda c: c.isdigit() or c == ".", price_elem.get_text()))
                try:
                    price_val = float(raw_p) if raw_p else None
                except ValueError:
                    pass

            mrp_elem = card.select_one("div.product-price span.product-strike")
            mrp_val = None
            if mrp_elem:
                raw_mrp = "".join(filter(lambda c: c.isdigit() or c == ".", mrp_elem.get_text()))
                try:
                    mrp_val = float(raw_mrp) if raw_mrp else None
                except ValueError:
                    pass

            rating_elem = card.select_one("div.product-ratingsContainer span, div[class*='ratingsContainer'] span, div[class*='Rating']")
            rating_val = None
            if rating_elem:
                try:
                    rating_val = float(re.findall(r"\d+\.?\d*", rating_elem.get_text(strip=True))[0])
                except (ValueError, IndexError):
                    pass
            elif card:
                m_rt = re.search(r"\b([3-5]\.\d)\s*(?:★|\|)?", card.get_text())
                if m_rt:
                    try:
                        rating_val = float(m_rt.group(1))
                    except ValueError:
                        pass

            rating_count_elem = card.select_one("div.product-ratingsCount, div.product-ratingsContainer div, span[class*='ratingsCount'], div[class*='ratingsCount']")
            rating_count_val = None
            if rating_count_elem:
                raw_rc = rating_count_elem.get_text(strip=True).replace("|", "").strip().lower()
                if "k" in raw_rc:
                    try:
                        rating_count_val = int(float(re.findall(r"\d+\.?\d*", raw_rc)[0]) * 1000)
                    except Exception:
                        pass
                else:
                    digits = re.sub(r"[^\d]", "", raw_rc)
                    if digits:
                        try:
                            rating_count_val = int(digits)
                        except ValueError:
                            pass

            link_elem = card.select_one("a[href]")
            href = link_elem.get("href", "") if link_elem else ""
            full_url = urllib.parse.urljoin("https://www.myntra.com/", href)

            items.append(
                Item(
                    source_id="myntra",
                    title=title,
                    brand=brand,
                    price=price_val,
                    mrp=mrp_val,
                    rating=rating_val,
                    rating_count=rating_count_val,
                    position=idx,
                    url=full_url,
                )
            )

        if not items:
            spec = get_source_spec("myntra")
            items = parse_dom(raw, spec=spec, source_id="myntra")

        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        # Suggest endpoint returns 401 without specific app headers; return empty list gracefully
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("myntra")
        settings = get_settings()
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        clean_q = re.sub(r"[^\w\s-]", "", query).strip().replace(" ", "-")
        url = f"https://www.myntra.com/{clean_q}?sort=popularity"

        context = await browser_mgr.get_context("myntra")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "myntra", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="myntra",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="Myntra bot check triggered.",
                )

            # Check if embedded JSON yielded items
            items = extract_embedded_json("myntra", content)
            strategy = "embedded_json"
            if not items:
                items = self.parse(content)
                strategy = "dom_selectors"

            items = items[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="myntra",
                status=status,
                strategy_used=strategy if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Myntra search failed: {e}")
            return SourceResult(
                source_id="myntra",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = MyntraAdapter().parse
