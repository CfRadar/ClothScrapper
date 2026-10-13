"""
Strategy 2: Embedded JSON state extraction from page HTML.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from bs4 import BeautifulSoup

from backend.app.scrapers.base import Item

logger = logging.getLogger("backend.scrapers.strategies.embedded_json")


def extract_embedded_json(source_id: str, html: str) -> list[Item]:
    """
    Extracts structured product items from embedded script tags.
    Gracefully handles (source_id, html) or (html, source_id).
    """
    if "<" in source_id or len(source_id) > 60:
        source_id, html = html, source_id

    items: list[Item] = []

    # 1. Myntra: window.__myntraState
    if source_id == "myntra" or "window.__myntraState" in html:
        idx = html.find("window.__myntraState")
        if idx != -1:
            eq_idx = html.find("=", idx)
            if eq_idx != -1:
                raw_tail = html[eq_idx + 1:].strip()
                parsed_json = None
                try:
                    if raw_tail.startswith("JSON.parse("):
                        inner_match = re.search(r'JSON\.parse\((["\'].*?["\'])\)', raw_tail, re.DOTALL)
                        if inner_match:
                            parsed_json = json.loads(json.loads(inner_match.group(1)))
                    elif raw_tail.startswith("{"):
                        end_script = raw_tail.find("</script>")
                        cand = raw_tail[:end_script].rstrip(" ;\n\r") if end_script != -1 else raw_tail
                        last_brace = cand.rfind("}")
                        if last_brace != -1:
                            parsed_json = json.loads(cand[:last_brace + 1])
                except Exception as e:
                    logger.debug(f"Failed parsing window.__myntraState JSON: {e}")

                if parsed_json and isinstance(parsed_json, dict):
                    products = (
                        parsed_json.get("searchData", {})
                        .get("results", {})
                        .get("products", [])
                    )
                    for idx, p in enumerate(products):
                        brand = p.get("brand")
                        prod_name = p.get("product", p.get("productName", "")).strip()
                        extra = p.get("additionalInfo", "")
                        title = f"{prod_name} {extra}".strip() if extra else prod_name
                        if not title:
                            title = f"{brand or ''} {prod_name}".strip()
                        if not title:
                            continue
                        items.append(
                            Item(
                                source_id="myntra",
                                title=title,
                                brand=brand,
                                price=float(p.get("price", 0)) if p.get("price") else None,
                                mrp=float(p.get("mrp", 0)) if p.get("mrp") else None,
                                rating=float(p.get("rating", 0)) if p.get("rating") else None,
                                rating_count=p.get("ratingCount"),
                                position=idx + 1,
                                sponsored=bool(p.get("isAd")),
                                url=f"https://www.myntra.com/{p.get('landingPageUrl', '')}",
                            )
                        )
                    if items:
                        return items

    # 2. Next.js: __NEXT_DATA__
    if "__NEXT_DATA__" in html:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                data = json.loads(script.string)
                page_props = data.get("props", {}).get("pageProps", {})
                products = (
                    page_props.get("products")
                    or page_props.get("items")
                    or page_props.get("initialData", {}).get("products", [])
                )
                if isinstance(products, list):
                    for idx, p in enumerate(products):
                        if isinstance(p, dict):
                            title = p.get("title", p.get("name", "")).strip()
                            if title:
                                items.append(
                                    Item(
                                        source_id=source_id,
                                        title=title,
                                        brand=p.get("brand"),
                                        price=float(p.get("price", 0)) if p.get("price") else None,
                                        position=idx + 1,
                                    )
                                )
                    if items:
                        return items
            except Exception as e:
                logger.debug(f"Failed parsing __NEXT_DATA__: {e}")

    # 3. JSON-LD: application/ld+json
    soup = BeautifulSoup(html, "html.parser")
    for s in soup.find_all("script", type="application/ld+json"):
        if not s.string:
            continue
        try:
            ld = json.loads(s.string)
            # ItemList
            if isinstance(ld, dict) and ld.get("@type") == "ItemList":
                elem_list = ld.get("itemListElement", [])
                for idx, elem in enumerate(elem_list):
                    item_data = elem.get("item", elem) if isinstance(elem, dict) else {}
                    title = item_data.get("name", "").strip()
                    if title:
                        items.append(
                            Item(
                                source_id=source_id,
                                title=title,
                                position=idx + 1,
                                url=item_data.get("url"),
                            )
                        )
                if items:
                    return items
        except Exception:
            continue

    return items
