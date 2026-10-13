"""
Strategy 3: Network capture of internal JSON XHR/fetch responses during page load.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.scrapers.base import Item

logger = logging.getLogger("backend.scrapers.strategies.network_capture")


def parse_captured_network_json(source_id: str, captured_payloads: list[dict[str, Any]]) -> list[Item]:
    """
    Scans captured network JSON responses for product arrays.
    """
    items: list[Item] = []

    for payload in captured_payloads:
        # Check standard product array keys
        candidate_arrays = []
        if isinstance(payload, dict):
            for k in ("products", "items", "searchResults", "data", "results", "itemList"):
                val = payload.get(k)
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    candidate_arrays.append(val)
                elif isinstance(val, dict):
                    # Nested data.products
                    nested_val = val.get("products") or val.get("items")
                    if isinstance(nested_val, list):
                        candidate_arrays.append(nested_val)

        for p_list in candidate_arrays:
            for idx, p in enumerate(p_list):
                title = p.get("name") or p.get("title") or p.get("productName") or p.get("fnlColorVariantData", {}).get("brandName")
                if not title or not isinstance(title, str):
                    continue

                price_raw = p.get("price")
                price_val: float | None = None
                if isinstance(price_raw, (int, float)):
                    price_val = float(price_raw)
                elif isinstance(price_raw, dict):
                    price_val = float(price_raw.get("value", 0)) if price_raw.get("value") else None

                brand = p.get("brand") or p.get("brandName")
                if not brand and isinstance(p.get("fnlColorVariantData"), dict):
                    brand = p["fnlColorVariantData"].get("brandName")

                items.append(
                    Item(
                        source_id=source_id,
                        title=title.strip(),
                        brand=brand,
                        price=price_val,
                        position=len(items) + 1,
                        url=p.get("url") or p.get("link"),
                    )
                )

        if len(items) >= 5:
            break

    return items


capture_network_json = parse_captured_network_json
