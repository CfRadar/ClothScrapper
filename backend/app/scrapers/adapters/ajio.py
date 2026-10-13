"""
Ajio B2C Marketplace Source Adapter.
Conforms to SourceAdapter Protocol.
Strategy ladder:
3. Network capture of internal XHR/fetch JSON during SPA navigation
2. Embedded state extraction
4. DOM selector fallback: div.rilrtl-products-list__item
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any
from bs4 import BeautifulSoup

from backend.app.config import get_settings
from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec
from backend.app.scrapers.strategies.dom_selectors import parse_dom
from backend.app.scrapers.strategies.network_capture import parse_captured_network_json

logger = logging.getLogger("backend.scrapers.adapters.ajio")


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    clean = "".join(filter(lambda c: c.isdigit() or c == ".", text))
    try:
        return float(clean) if clean else None
    except ValueError:
        return None


class AjioAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="ajio",
            group="B2C",
            kind="marketplace",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """
        Pure parser function. Handles both captured network JSON payloads
        and rendered HTML string fallback.
        """
        # If payload is dict or captured payloads list
        if isinstance(raw, dict):
            return parse_captured_network_json("ajio", [raw])
        if isinstance(raw, list):
            return parse_captured_network_json("ajio", raw)

        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("div.rilrtl-products-list__item, div.item")
        items: list[Item] = []

        for idx, card in enumerate(cards, 1):
            brand_el = card.select_one("div.brand, span.brand-name")
            title_el = card.select_one("div.nameCls, .product-title, .title")
            brand = brand_el.get_text(strip=True) if brand_el else None
            title = title_el.get_text(strip=True) if title_el else ""

            if not title and brand:
                title = brand

            if not title or len(title) < 3:
                continue

            price_el = card.select_one("span.price, .discounted-price, span.orgl-price")
            price = parse_price(price_el.get_text(strip=True) if price_el else None)

            link_el = card.select_one("a.rilrtl-products-list__link, a[href]")
            href = link_el.get("href", "") if link_el else ""
            full_url = urllib.parse.urljoin("https://www.ajio.com", href)

            items.append(
                Item(
                    source_id="ajio",
                    title=f"{brand + ' ' if brand and brand not in title else ''}{title}".strip(),
                    brand=brand,
                    price=price,
                    position=idx,
                    url=full_url,
                )
            )

        if not items:
            spec = get_source_spec("ajio")
            items = parse_dom(raw, spec=spec, source_id="ajio")

        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("ajio")
        settings = get_settings()
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.ajio.com/search/?text={encoded}"

        context = await browser_mgr.get_context("ajio")
        page = await context.new_page()

        captured_json: list[dict[str, Any]] = []

        async def response_listener(response):
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct and "api" in response.url:
                    body = await response.json()
                    if isinstance(body, dict):
                        captured_json.append(body)
            except Exception:
                pass

        page.on("response", response_listener)

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "ajio", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="ajio",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="Ajio bot challenge triggered.",
                )

            # Strategy 3: Check network captured JSON
            items = parse_captured_network_json("ajio", captured_json)
            strategy = "network_capture"

            # Strategy 4: Fallback to DOM parsing
            if not items:
                items = self.parse(content)
                strategy = "dom_selectors"

            items = items[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="ajio",
                status=status,
                strategy_used=strategy if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Ajio search failed: {e}")
            return SourceResult(
                source_id="ajio",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = AjioAdapter().parse
