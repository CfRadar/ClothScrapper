"""
Strategy 5: Structural Heuristics parsing.
Fuzzy keyword, price-marker, and block extraction as an ultimate fallback
when DOM selectors and embedded state fail.
"""

from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup, Tag

try:
    from backend.app.scrapers.base import Item
except ImportError:
    from app.scrapers.base import Item

logger = logging.getLogger("backend.scrapers.strategies.heuristics")

PRICE_REGEX = re.compile(r"(?:₹|Rs\.?|INR|\$)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


def parse_heuristics(html: str, source_id: str) -> list[Item]:
    """
    Scans HTML for repeating structural containers that contain price markers and titles.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: list[Item] = []
    seen_titles: set[str] = set()

    # Look for elements containing price symbols
    candidates = soup.find_all(string=PRICE_REGEX)
    
    for match in candidates:
        parent = match.parent
        if not parent or not isinstance(parent, Tag):
            continue
        
        # Traverse up to find a sensible card container (limit to 4 levels)
        container = parent
        for _ in range(4):
            if container.parent and isinstance(container.parent, Tag) and container.parent.name not in ["body", "html"]:
                container = container.parent
            else:
                break
        
        # Extract title candidates within container
        headers = container.find_all(["h1", "h2", "h3", "h4", "a", "p", "span"])
        best_title = None
        for h in headers:
            text = h.get_text(strip=True)
            # Filter plausible product title lengths
            if 15 <= len(text) <= 120 and not PRICE_REGEX.search(text):
                best_title = text
                break
        
        if not best_title or best_title in seen_titles:
            continue
        seen_titles.add(best_title)

        # Parse price
        price_val = None
        price_match = PRICE_REGEX.search(parent.get_text())
        if price_match:
            try:
                price_val = float(price_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Look for links
        url = None
        link = container.find("a", href=True)
        if link and isinstance(link, Tag):
            url = str(link.get("href"))

        items.append(
            Item(
                source_id=source_id,
                title=best_title,
                price=price_val,
                position=len(items) + 1,
                url=url,
            )
        )
        if len(items) >= 40:
            break

    return items
