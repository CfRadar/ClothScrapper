"""
Generic Custom Source Adapter (handles 'estay' and any future custom user sources).
Conforms to SourceAdapter Protocol.
Configured via sources.yaml. If unconfigured, remains disabled/unavailable.
"""

from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Any

from backend.app.config import get_settings
from backend.app.scrapers.base import BaseSourceAdapter, Item, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec
from backend.app.scrapers.strategies.dom_selectors import parse_dom
from backend.app.scrapers.strategies.heuristics import parse_heuristics

logger = logging.getLogger("backend.scrapers.adapters.generic_custom")


class GenericCustomAdapter(BaseSourceAdapter):
    def __init__(self, source_id: str = "estay"):
        spec = get_source_spec(source_id)
        group = spec.group if spec else "Custom"
        kind = spec.kind if spec else "marketplace"
        roles = [str(r) for r in spec.roles] if spec else ["sell_target"]

        super().__init__(
            source_id=source_id,
            group=group,
            kind=kind,
            roles=roles,
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        if not isinstance(raw, str):
            return []
        spec = get_source_spec(self.id)
        items = parse_dom(raw, spec=spec, source_id=self.id)
        if not items:
            items = parse_heuristics(raw, self.id)
        return items

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        spec = get_source_spec(self.id)

        if spec and spec.status_override:
            return SourceResult(
                source_id=self.id,
                status="unavailable" if spec.status_override in ("unavailable", "disabled") else spec.status_override,
                cause="wrong_url",
                items=[],
                note=spec.status_reason or f"Generic source '{self.id}' is currently {spec.status_override}.",
            )

        if not spec or not spec.url_templates.get("search"):
            return SourceResult(
                source_id=self.id,
                status="unavailable",
                cause="wrong_url",
                items=[],
                note=(
                    f"Generic source '{self.id}' disabled until search_url_template "
                    f"and selectors are configured in sources.yaml."
                ),
            )

        browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
        encoded = urllib.parse.quote_plus(query)
        template = spec.url_templates["search"]
        url = template.format(query=encoded)

        context = await browser_mgr.get_context(self.id)
        page = await context.new_page()

        try:
            is_blocked, content = await browser_mgr.polite_goto(page, url, self.id, spec=spec)
            duration_ms = int((time.time() - start_time) * 1000)

            if is_blocked:
                return SourceResult(
                    source_id=self.id,
                    status="blocked",
                    cause="blocked",
                    duration_ms=duration_ms,
                    note=f"Custom source {self.id} bot block triggered.",
                )

            items = self.parse(content)
            status = "ok" if len(items) >= 3 else ("partial" if items else "error")

            return SourceResult(
                source_id=self.id,
                status=status,
                strategy_used="dom_selectors" if items else None,
                items=items,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Custom source {self.id} search failed: {e}")
            return SourceResult(
                source_id=self.id,
                status="error",
                cause="timing",
                duration_ms=duration_ms,
                note=str(e),
            )
        finally:
            await page.close()
