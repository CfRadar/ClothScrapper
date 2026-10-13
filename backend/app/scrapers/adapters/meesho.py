"""
Meesho B2C Marketplace Source Adapter.
Strategy ladder:
1. Embedded JSON extraction (e.g. Next.js __NEXT_DATA__)
2. Network capture of search XHR/fetch JSON
3. DOM selector parsing: div[class*='ProductList__GridCol'], div[class*='Card__BaseCard']
4. Heuristics fallback
"""

from __future__ import annotations

import json
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

logger = logging.getLogger("backend.scrapers.adapters.meesho")


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    clean = "".join(filter(lambda c: c.isdigit() or c == ".", text))
    try:
        return float(clean) if clean else None
    except ValueError:
        return None


class MeeshoAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="meesho",
            group="B2C",
            kind="marketplace",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """
        Pure parser function. Handles JSON dictionaries, lists of captured network
        payloads, Next.js __NEXT_DATA__ embedded script tags, or DOM fallback.
        """
        if isinstance(raw, dict):
            return self._parse_json_dict(raw)
        if isinstance(raw, list):
            for entry in raw:
                items = self._parse_json_dict(entry)
                if items:
                    return items
            return []

        if not isinstance(raw, str):
            return []

        # 1. Embedded JSON extraction from __NEXT_DATA__
        soup = BeautifulSoup(raw, "html.parser")
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        if next_data_script and next_data_script.string:
            try:
                data = json.loads(next_data_script.string)
                items = self._extract_from_next_data(data)
                if items:
                    return items
            except Exception as e:
                logger.debug(f"Failed to parse __NEXT_DATA__ for Meesho: {e}")

        # 2. DOM Selector fallback
        items: list[Item] = []
        cards = soup.select(
            "div[class*='ProductList__GridCol'], div[class*='Card__BaseCard'], div[data-testid='product-card'], div[class*='sc-bcXHqe']"
        )
        for idx, card in enumerate(cards[:40]):
            title_el = card.select_one("p[class*='Card__Title'], p[class*='ProductTitle'], h5, p.title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            price_el = card.select_one("h5[class*='Heading'], span[class*='Price'], div[class*='Price']")
            price = parse_price(price_el.get_text(strip=True)) if price_el else None

            mrp_el = card.select_one("span[class*='StrikedOffPrice'], span[class*='mrp']")
            mrp = parse_price(mrp_el.get_text(strip=True)) if mrp_el else None

            rating_el = card.select_one("span[class*='Badge__BadgeStyle'], div[class*='Rating']")
            rating = None
            if rating_el:
                try:
                    rating = float(re.findall(r"\d+\.?\d*", rating_el.get_text(strip=True))[0])
                except Exception:
                    pass

            rating_count = None
            rc_el = card.select_one("span[class*='RatingCount'], span[class*='Reviews'], span[class*='review'], p[class*='Reviews']")
            if rc_el:
                rc_txt = rc_el.get_text(strip=True).lower()
                if "k" in rc_txt:
                    try:
                        rating_count = int(float(re.findall(r"\d+\.?\d*", rc_txt)[0]) * 1000)
                    except Exception:
                        pass
                else:
                    digits = re.sub(r"[^\d]", "", rc_txt)
                    if digits:
                        try:
                            rating_count = int(digits)
                        except Exception:
                            pass

            link_el = card.select_one("a[href]")
            href = link_el.get("href") if link_el else ""
            if href and not href.startswith("http"):
                href = f"https://www.meesho.com{href}"

            items.append(
                Item(
                    source_id="meesho",
                    title=title,
                    brand=None,  # Meesho items usually have no brand; do not invent one
                    price=price,
                    mrp=mrp,
                    rating=rating,
                    rating_count=rating_count,
                    position=idx + 1,
                    url=href or "https://www.meesho.com",
                )
            )

        return items

    def _extract_from_next_data(self, data: dict[str, Any]) -> list[Item]:
        items: list[Item] = []
        page_props = data.get("props", {}).get("pageProps", {})
        initial_state = page_props.get("initialState", {}) or page_props.get("data", {})
        products = (
            initial_state.get("products", [])
            or page_props.get("products", [])
            or initial_state.get("searchData", {}).get("products", [])
        )
        if isinstance(products, list):
            for idx, p in enumerate(products[:40]):
                if not isinstance(p, dict):
                    continue
                title = p.get("name") or p.get("title") or ""
                if not title:
                    continue
                price = float(p.get("discounted_price") or p.get("price") or 0) or None
                mrp = float(p.get("original_price") or p.get("mrp") or 0) or None
                rating = float(p.get("rating") or 0) or None
                rating_count = None
                try:
                    rc_raw = p.get("review_count") or p.get("reviews_count") or p.get("rating_count") or p.get("reviews")
                    if rc_raw:
                        rating_count = int(rc_raw)
                except (ValueError, TypeError):
                    pass
                items.append(
                    Item(
                        source_id="meesho",
                        title=title,
                        brand=None,
                        price=price,
                        mrp=mrp,
                        rating=rating,
                        rating_count=rating_count,
                        position=idx + 1,
                        url=p.get("url") or f"https://www.meesho.com/p/{p.get('id', '')}",
                    )
                )
        return items

    def _parse_json_dict(self, data: dict[str, Any]) -> list[Item]:
        items: list[Item] = []
        products = data.get("products") or data.get("catalogList", []) or data.get("items", [])
        if isinstance(products, list):
            for idx, p in enumerate(products[:40]):
                if not isinstance(p, dict):
                    continue
                title = p.get("name") or p.get("title") or ""
                if not title:
                    continue
                price = float(p.get("discounted_price") or p.get("price") or 0) or None
                mrp = float(p.get("original_price") or p.get("mrp") or 0) or None
                rating = float(p.get("rating") or 0) or None
                rating_count = None
                try:
                    rc_raw = p.get("review_count") or p.get("reviews_count") or p.get("rating_count") or p.get("reviews")
                    if rc_raw:
                        rating_count = int(rc_raw)
                except (ValueError, TypeError):
                    pass
                items.append(
                    Item(
                        source_id="meesho",
                        title=title,
                        brand=None,
                        price=price,
                        mrp=mrp,
                        rating=rating,
                        rating_count=rating_count,
                        position=idx + 1,
                        url=p.get("url") or f"https://www.meesho.com/p/{p.get('id', '')}",
                    )
                )
        return items

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        settings = get_settings()
        spec = get_source_spec("meesho")
        start_t = time.time()

        if getattr(settings, "OFFLINE_FIXTURES", False):
            logger.info("OFFLINE_FIXTURES is active, attempting to load meesho_search.html fixture")
            import os
            fixture_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "tests", "fixtures", "meesho_search.html"
            )
            if os.path.exists(fixture_path):
                with open(fixture_path, "r", encoding="utf-8") as f:
                    content = f.read()
                items = self.parse(content)
                dur = int(round((time.time() - start_t) * 1000))
                return SourceResult(
                    source_id="meesho",
                    status="ok",
                    strategy_used="offline_fixture",
                    items=items,
                    duration_ms=dur,
                )

        encoded_q = urllib.parse.quote_plus(query)
        search_url = f"https://www.meesho.com/search?q={encoded_q}&sort=rating_high"

        bm = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
        captured_payloads: list[dict[str, Any]] = []

        async def response_interceptor(response):
            if "search" in response.url or "product" in response.url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        captured_payloads.append(body)
                except Exception:
                    pass

        try:
            async with bm.page(
                source_id="meesho",
                block_images=spec.block_images if spec else False,
                response_listener=response_interceptor,
            ) as page:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=12000)

                # Dismiss app banner / login prompt if present
                for dismiss_sel in [
                    "button:has-text('✕')",
                    "div[class*='Modal'] button",
                    "button:has-text('Close')",
                    "span:has-text('Continue on Web')",
                ]:
                    try:
                        btn = page.locator(dismiss_sel).first
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                    except Exception:
                        pass

                # Scroll down 2 steps
                await bm.step_scroll(page, steps=2, pause_ms=400)
                html = await page.content()

            # Check network capture first
            if captured_payloads:
                items = self.parse(captured_payloads)
                if items:
                    dur = int(round((time.time() - start_t) * 1000))
                    return SourceResult(
                        source_id="meesho",
                        status="ok",
                        strategy_used="network_capture",
                        items=items,
                        duration_ms=dur,
                    )

            # Fallback to HTML parser
            items = self.parse(html)
            dur = int(round((time.time() - start_t) * 1000))
            status = "ok" if items else "blocked"
            return SourceResult(
                source_id="meesho",
                status=status,
                strategy_used="dom_selectors" if items else "none",
                items=items,
                duration_ms=dur,
                error="No items extracted from Meesho search page" if not items else None,
            )
        except Exception as exc:
            dur = int(round((time.time() - start_t) * 1000))
            logger.warning(f"Meesho fetch failed: {exc}")
            return SourceResult(
                source_id="meesho",
                status="blocked" if "block" in str(exc).lower() else "error",
                strategy_used="none",
                items=[],
                duration_ms=dur,
                error=str(exc),
            )

    fetch = search
