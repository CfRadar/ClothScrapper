#!/usr/bin/env python3
"""
Scaffolding generator for new Marketplace Keyword Agent source adapters.
Usage:
    python new_source.py --id ajio --label "Ajio" --group marketplaces --kind marketplace --hosts "ajio.com,www.ajio.com"
"""

import argparse
import os
import sys

ADAPTER_TEMPLATE = '''"""
Source adapter for {label} ({id}).
Implements SourceAdapter protocol with 5-step strategy ladder.
"""

import logging
from typing import Any
from urllib.parse import quote_plus

from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult, HealthReport

logger = logging.getLogger("backend.scrapers.{id}")


class {class_name}Adapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="{id}",
            group="{group}",
            kind="{kind}",
            roles={roles},
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """
        Pure deterministic parser. Turns HTML or JSON payload into validated Item models.
        """
        items: list[Item] = []
        if isinstance(raw, dict):
            # Parse JSON payload (Strategy 1, 2, or 3)
            products = raw.get("products", raw.get("items", []))
            for idx, p in enumerate(products):
                title = p.get("name", p.get("title", "")).strip()
                if not title:
                    continue
                items.append(
                    Item(
                        title=title,
                        brand=p.get("brand", ""),
                        price=float(p.get("price", 0)) if p.get("price") else None,
                        mrp=float(p.get("mrp", 0)) if p.get("mrp") else None,
                        position=idx + 1,
                        source_id=self.id,
                        url=p.get("url", ""),
                    )
                )
            return items

        # Fallback DOM Parser
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        cards = soup.select("div.product-card, div.card, article")
        for idx, card in enumerate(cards):
            title_elem = card.select_one("h2, h3, a.title, .product-title")
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            items.append(
                Item(
                    title=title,
                    position=idx + 1,
                    source_id=self.id,
                )
            )
        return items

    async def suggest(self, query: str, ctx: Any) -> list[str]:
        """Fetch search suggestions or autocomplete phrases."""
        # TODO: Implement suggestion endpoint if available on {label}
        return []

    async def search(self, query: str, ctx: Any) -> SourceResult:
        """
        Execute search across the 5-step strategy ladder:
        1. Suggestion API
        2. Embedded JSON state
        3. Network capture
        4. DOM selectors
        5. Heuristic
        """
        encoded_query = quote_plus(query)
        # TODO: Implement search logic with browser_mgr or safe_http
        return SourceResult(
            source_id=self.id,
            status="ok",
            strategy_used="dom_selector",
            items=[],
            suggestions=[],
        )
'''

REGISTRY_SNIPPET = '''  - id: {id}
    label: "{label}"
    group: "{group}"
    kind: "{kind}"
    roles: {roles}
    default_enabled: true
    tos_risk: "low"
    relevance: "high"
    hosts:
{hosts_yaml}
    strategies:
      - "network_capture"
      - "dom_selector"
    url_templates:
      search: "https://www.{main_host}/search?q={{query}}"
    delay_min: 2
    delay_max: 5
    block_images: true
    notes: "{label} adapter for keyword intelligence."
'''


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Source Adapter")
    parser.add_argument("--id", required=True, help="Unique source id (e.g. ajio, zepto)")
    parser.add_argument("--label", required=True, help="Human readable label (e.g. Ajio)")
    parser.add_argument(
        "--group",
        required=True,
        choices=["marketplaces", "b2b", "quickcommerce", "signals"],
        help="Grouping category",
    )
    parser.add_argument(
        "--kind",
        required=True,
        choices=["marketplace", "b2b", "quickcommerce", "search", "social"],
        help="Source kind",
    )
    parser.add_argument(
        "--hosts",
        required=True,
        help="Comma-separated allowlisted hosts (e.g. ajio.com,www.ajio.com)",
    )
    parser.add_argument(
        "--role",
        default="signal",
        choices=["sell_target", "signal", "both"],
        help="Source operational role",
    )

    args = parser.parse_args()
    source_id = args.id.lower().replace("-", "_")
    class_name = "".join(part.capitalize() for part in source_id.split("_"))

    roles = ["sell_target", "signal"] if args.role == "both" else [args.role]
    hosts_list = [h.strip() for h in args.hosts.split(",") if h.strip()]
    hosts_yaml = "\n".join(f'      - "{h}"' for h in hosts_list)
    main_host = hosts_list[0] if hosts_list else f"{source_id}.com"

    # 1. Generate Adapter File
    adapter_dir = os.path.join("backend", "app", "scrapers")
    os.makedirs(adapter_dir, exist_ok=True)
    adapter_path = os.path.join(adapter_dir, f"{source_id}.py")

    content = ADAPTER_TEMPLATE.format(
        id=source_id,
        label=args.label,
        group=args.group,
        kind=args.kind,
        roles=roles,
        class_name=class_name,
    )

    if not os.path.exists(adapter_path):
        with open(adapter_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Created adapter: {adapter_path}")
    else:
        print(f"[*] Adapter already exists at {adapter_path}")

    # 2. Create Fixture Directory
    fixture_dir = os.path.join("backend", "tests", "fixtures", source_id)
    os.makedirs(fixture_dir, exist_ok=True)
    placeholder_fixture = os.path.join(fixture_dir, "canary.html")
    if not os.path.exists(placeholder_fixture):
        with open(placeholder_fixture, "w", encoding="utf-8") as f:
            f.write(f"<!-- Canary test fixture for {args.label} -->\\n<div>Placeholder</div>\\n")
        print(f"[+] Created test fixture folder: {fixture_dir}")

    # 3. Print Registry Template
    print("\\n=== Add this snippet to backend/app/scrapers/sources.yaml ===")
    snippet = REGISTRY_SNIPPET.format(
        id=source_id,
        label=args.label,
        group=args.group,
        kind=args.kind,
        roles=roles,
        hosts_yaml=hosts_yaml,
        main_host=main_host,
    )
    print(snippet)
    print("=============================================================")


if __name__ == "__main__":
    main()
