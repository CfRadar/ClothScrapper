"""
Strategy 4: DOM Selectors parsing with fallback chains.
Pure, deterministic parsing decoupled from network/browser logic.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from bs4 import BeautifulSoup, Tag

try:
    from backend.app.scrapers.base import Item, B2BInfo
    from backend.app.scrapers.registry import SourceSpec
except ImportError:
    from app.scrapers.base import Item, B2BInfo
    from app.scrapers.registry import SourceSpec

logger = logging.getLogger("backend.scrapers.strategies.dom_selectors")


def _clean_text(el: Tag | None) -> str | None:
    if not el:
        return None
    text = el.get_text(separator=" ", strip=True)
    return text if text else None


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    clean = re.sub(r"[^\d.]", "", text)
    try:
        return float(clean)
    except ValueError:
        return None


def _select_first(element: Tag, selector_chain: str) -> Tag | None:
    """Tries selectors separated by comma or evaluates single selector."""
    selectors = [s.strip() for s in selector_chain.split(",") if s.strip()]
    for sel in selectors:
        match = element.select_one(sel)
        if match:
            return match
    return None


def parse_dom(
    html: str,
    spec: SourceSpec | None = None,
    container_selector: str | None = None,
    field_selectors: dict[str, str] | None = None,
    source_id: str = "custom",
) -> list[Item]:
    """
    Extracts Items from an HTML string using container and field selector fallbacks.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    src_id = spec.id if spec else source_id
    selectors = spec.selectors if spec else (field_selectors or {})
    
    container_sel = container_selector or selectors.get("container") or selectors.get("card")
    if not container_sel:
        # Default fallback to common product container classes
        container_sel = (
            "div[data-component-type='s-search-result'], "
            "li.product-base, "
            "div._75nlfW, div._1AtVbE, "
            "div.rilrtl-products-list__item, "
            "div.product-card, div.item-card"
        )

    # Find cards using container fallback
    cards: list[Tag] = []
    for sel in [s.strip() for s in container_sel.split(",") if s.strip()]:
        matched = soup.select(sel)
        if matched:
            cards = matched
            break

    items: list[Item] = []
    title_sel = selectors.get("title", "h2, h3, .product-title, .title, a.title")
    brand_sel = selectors.get("brand", ".brand, .product-brand, .brand-name")
    price_sel = selectors.get("price", ".price, .product-price, .discounted-price, span.a-price-whole")
    mrp_sel = selectors.get("mrp", ".mrp, .original-price, .strike, .a-text-price")
    rating_sel = selectors.get("rating", ".rating, .product-rating, .stars, span.a-icon-alt")
    rating_count_sel = selectors.get("rating_count", ".rating-count, .reviews, span.a-size-base.s-underline-text")
    url_sel = selectors.get("url", "a[href*='/dp/'], a[href*='/p/'], a.product-link, a")

    # B2B fields
    supplier_sel = selectors.get("supplier", ".company-name, .supplier-name, .seller-name")
    location_sel = selectors.get("location", ".city, .supplier-location, .location")
    moq_sel = selectors.get("moq", ".moq, .min-order, .order-quantity")
    unit_sel = selectors.get("unit", ".price-unit, .unit")
    price_range_sel = selectors.get("price_range", ".price-range, .price-slab")

    for pos, card in enumerate(cards[:60], start=1):
        # Extract title
        title_el = _select_first(card, title_sel)
        title = _clean_text(title_el)
        if not title:
            # Fallback: check aria-label or img alt
            img = card.select_one("img[alt]")
            if img and img.get("alt"):
                title = str(img.get("alt")).strip()
        
        if not title or len(title) < 3:
            continue

        brand = _clean_text(_select_first(card, brand_sel))
        price = _parse_price(_clean_text(_select_first(card, price_sel)))
        mrp = _parse_price(_clean_text(_select_first(card, mrp_sel)))
        
        rating_text = _clean_text(_select_first(card, rating_sel))
        rating = None
        if rating_text:
            match = re.search(r"(\d+(\.\d+)?)", rating_text)
            if match:
                try:
                    rating = float(match.group(1))
                except ValueError:
                    pass

        rating_count_text = _clean_text(_select_first(card, rating_count_sel))
        rating_count = None
        if rating_count_text:
            clean_rc = re.sub(r"[^\d]", "", rating_count_text)
            if clean_rc:
                try:
                    rating_count = int(clean_rc)
                except ValueError:
                    pass

        # URL
        url = None
        url_el = _select_first(card, url_sel)
        if url_el and url_el.get("href"):
            url = str(url_el.get("href"))

        # B2B details
        b2b_info = None
        if spec and spec.kind == "b2b":
            supplier = _clean_text(_select_first(card, supplier_sel))
            location = _clean_text(_select_first(card, location_sel))
            moq = _clean_text(_select_first(card, moq_sel))
            unit = _clean_text(_select_first(card, unit_sel))
            price_range = _clean_text(_select_first(card, price_range_sel))
            verified = bool(card.select_one(".verified, .truststamp, [data-verified='true']"))
            
            b2b_info = B2BInfo(
                supplier=supplier,
                location=location,
                moq=moq,
                unit=unit,
                price_range=price_range,
                verified=verified,
            )

        items.append(
            Item(
                source_id=src_id,
                title=title,
                brand=brand,
                price=price,
                mrp=mrp,
                rating=rating,
                rating_count=rating_count,
                position=pos,
                sponsored=bool("sponsored" in title.lower() or card.select_one(".sponsored, [data-sponsored='true']")),
                url=url,
                b2b=b2b_info,
            )
        )

    return items
