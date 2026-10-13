"""
Flipkart B2C Marketplace Source Adapter.
Conforms to SourceAdapter Protocol.
Strategy ladder:
4. DOM structural anchors (/p/, pid=, div[data-id])
5. Heuristics fallback
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
from backend.app.scrapers.strategies.heuristics import parse_heuristics

logger = logging.getLogger("backend.scrapers.adapters.flipkart")


def parse_price_regex(text: str) -> float | None:
    match = re.search(r"₹\s*([\d,]+)", text)
    if match:
        digits = match.group(1).replace(",", "")
        try:
            return float(digits)
        except ValueError:
            return None
    return None


def parse_rating_regex(text: str) -> float | None:
    match = re.search(r"\b([1-5]\.\d)\b", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


class FlipkartAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="flipkart",
            group="B2C",
            kind="marketplace",
            roles=["sell_target", "signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """
        Pure parser function. Structural parser for Flipkart's obfuscated CSS classes.
        Finds product cards with data-id or anchors targeting product links (/p/ or pid=).
        """
        if not isinstance(raw, str):
            return []

        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("div[data-id]")
        if not cards:
            cards = [
                a.parent
                for a in soup.select('a[href*="/p/"]')
                if a.parent and len(a.parent.get_text()) > 30
            ]

        items: list[Item] = []

        for idx, card in enumerate(cards, 1):
            link = card.select_one('a[href*="/p/"]') or card.select_one('a[href*="pid="]')
            href = link.get("href", "") if link else ""
            if not href:
                continue
            full_url = urllib.parse.urljoin("https://www.flipkart.com", href)

            # Title
            title_elem = (
                card.select_one("a.WKTcLC")
                or card.select_one("a.IRpwTa")
                or card.select_one("div.KzDlHZ")
                or card.select_one("div._4rR01T")
                or link
            )
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Brand
            brand_elem = card.select_one("div._2WkVRV") or card.select_one("div._2W9cHo") or card.select_one("div.syl9yP")
            brand = brand_elem.get_text(strip=True) if brand_elem else None

            # Price
            price_elem = card.select_one("div.Nx9bqj") or card.select_one("div._30jeq3")
            price = None
            if price_elem:
                price = parse_price_regex(price_elem.get_text())

            # MRP
            mrp_elem = card.select_one("div.yRaY8j") or card.select_one("div._3I9_wc")
            mrp = None
            if mrp_elem:
                mrp = parse_price_regex(mrp_elem.get_text())

            # Rating
            rating_elem = (
                card.select_one("div.XQDdHH")
                or card.select_one("div._3LWZlK")
                or card.select_one("div._5OesEi")
                or card.select_one("div[class*='XQDdHH']")
                or card.select_one("div[class*='_3LWZlK']")
                or card.select_one("span[id*='productRating']")
            )
            rating = None
            if rating_elem:
                rating = parse_rating_regex(rating_elem.get_text())
            elif card:
                # Regex fallback on card text for star rating (e.g. 4.2★)
                m_star = re.search(r"\b([3-5]\.\d)\s*(?:★|\*|\b)", card.get_text())
                if m_star:
                    try:
                        rating = float(m_star.group(1))
                    except ValueError:
                        pass

            rating_count_elem = (
                card.select_one("span.Wphh3N")
                or card.select_one("span._2_R_DZ")
                or card.select_one("span._13vcmD")
                or card.select_one("span[class*='Wphh3N']")
                or card.select_one("span[class*='_2_R_DZ']")
            )
            rating_count = None
            if rating_count_elem:
                raw_rc = rating_count_elem.get_text(strip=True).lower()
                if "k" in raw_rc:
                    try:
                        rating_count = int(float(re.findall(r"\d+\.?\d*", raw_rc)[0]) * 1000)
                    except Exception:
                        pass
                else:
                    digits = re.sub(r"[^\d]", "", raw_rc)
                    if digits:
                        try:
                            rating_count = int(digits)
                        except ValueError:
                            pass
            elif card:
                # Regex fallback for review count in parentheses (e.g. (1,820))
                m_rc = re.search(r"\(([\d,]+(?:\.\d+)?k?)\)", card.get_text())
                if m_rc:
                    rc_str = m_rc.group(1).lower()
                    if "k" in rc_str:
                        try:
                            rating_count = int(float(re.findall(r"\d+\.?\d*", rc_str)[0]) * 1000)
                        except Exception:
                            pass
                    else:
                        digits = re.sub(r"[^\d]", "", rc_str)
                        if digits:
                            try:
                                rating_count = int(digits)
                            except ValueError:
                                pass

            if not title or len(title) < 3:
                continue

            items.append(
                Item(
                    source_id="flipkart",
                    title=f"{brand + ' ' if brand and brand not in title else ''}{title}".strip(),
                    brand=brand,
                    price=price,
                    mrp=mrp,
                    rating=rating,
                    rating_count=rating_count,
                    position=idx,
                    url=full_url,
                )
            )

        if not items:
            spec = get_source_spec("flipkart")
            items = parse_dom(raw, spec=spec, source_id="flipkart")

        if not items:
            items = parse_heuristics(raw, "flipkart")

        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec("flipkart")
        settings = get_settings()
        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.flipkart.com/search?q={encoded}&sort=popularity"

        context = await browser_mgr.get_context("flipkart")
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, "flipkart", spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id="flipkart",
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note="Flipkart robot check triggered.",
                )

            items = self.parse(content)[: settings.MAX_PRODUCTS_PER_QUERY]
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")
            cause = None if status == "ok" else ("selector_drift" if not items else None)

            return SourceResult(
                source_id="flipkart",
                status=status,
                strategy_used="dom_selectors" if items else None,
                cause=cause,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Flipkart search failed: {e}")
            return SourceResult(
                source_id="flipkart",
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()


parse_search_html = FlipkartAdapter().parse
