"""
Google Search Signals Adapter.
Conforms to SourceAdapter Protocol.
Extracts search demand signals and autocomplete keywords.
Never uses Google Custom Search JSON API (retiring Jan 2027).
Uses suggestqueries.google.com autocomplete endpoint (low ToS risk).
Optional Brave/Serper provider integration; optional direct SERP scrape (behind flag).
"""

from __future__ import annotations

import asyncio
import logging
import time
import urllib.parse
from typing import Any

from backend.app.config import get_settings
from backend.app.net.safe_http import SafeAsyncClient
from backend.app.scrapers.base import BaseSourceAdapter, Item, SocialSignal, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.registry import get_source_spec

logger = logging.getLogger("backend.scrapers.adapters.google")

AUTOCOMPLETE_URL = (
    "https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=in&q={query}"
)


class GoogleSignalsAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="google",
            group="Search and social",
            kind="search",
            roles=["signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        return []

    async def suggest(self, query: str, ctx: Any = None) -> list[str]:
        """Fetch Google autocomplete suggestions for India region via HTTP."""
        encoded = urllib.parse.quote_plus(query)
        url = AUTOCOMPLETE_URL.format(query=encoded)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/124.0",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            async with SafeAsyncClient(headers=headers, timeout=6.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    # Firefox format: ["query", ["s1", "s2", ...]]
                    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                        return [str(s).strip() for s in data[1] if isinstance(s, str)]
        except Exception as e:
            logger.debug(f"Google autocomplete request failed: {e}")
        return []

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()
        settings = get_settings()

        # 1. Fetch autocomplete suggestions for query and top modifiers (max 4 queries)
        queries_to_probe = [
            query,
            f"{query} styling",
            f"{query} outfits",
            f"best {query}",
        ]

        all_suggestions: list[str] = []
        signals: list[SocialSignal] = []
        seen_phrases: set[str] = set()

        for q in queries_to_probe[:4]:
            s_list = await self.suggest(q)
            for s in s_list:
                s_clean = s.strip().lower()
                if s_clean and s_clean not in seen_phrases:
                    seen_phrases.add(s_clean)
                    all_suggestions.append(s_clean)
                    signals.append(
                        SocialSignal(
                            source="google",
                            phrase=s_clean,
                            mentions=1,
                            samples=[f"Search query: {q}"],
                        )
                    )
            await asyncio.sleep(0.3)  # Politeness interval

        related_searches: list[str] = []

        # 2. Check for optional third-party SEARCH_PROVIDER (brave / serper)
        provider = (settings.SEARCH_PROVIDER or "none").lower()
        provider_key = settings.SEARCH_PROVIDER_API_KEY.get_secret_value().strip()

        if provider == "serper" and provider_key:
            try:
                headers = {"X-API-KEY": provider_key, "Content-Type": "application/json"}
                async with SafeAsyncClient(headers=headers, timeout=8.0) as client:
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        json={"q": query, "gl": "in", "hl": "en"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("peopleAlsoAsk", []):
                            question = item.get("question")
                            if question:
                                related_searches.append(question)
                        for item in data.get("relatedSearches", []):
                            query_text = item.get("query")
                            if query_text:
                                related_searches.append(query_text)
            except Exception as e:
                logger.debug(f"Serper search provider failed: {e}")

        # 3. Direct SERP scraping only if explicitly enabled
        if settings.ENABLE_GOOGLE_SERP_SCRAPE:
            browser_mgr = ctx if isinstance(ctx, BrowserManager) else BrowserManager.get_instance()
            encoded = urllib.parse.quote_plus(query)
            serp_url = f"https://www.google.com/search?q={encoded}&gl=in&hl=en"
            context = await browser_mgr.get_context("google")
            page = await context.new_page()
            try:
                is_blocked, content = await browser_mgr.polite_goto(page, serp_url, "google")
                if is_blocked or "/sorry/" in page.url:
                    logger.warning("Google SERP /sorry/ or CAPTCHA page detected. Stopping politely.")
                    # Return autocomplete signals with warning
                    return SourceResult(
                        source_id="google",
                        status="partial",
                        strategy_used="suggest_endpoint",
                        suggestions=all_suggestions[:30],
                        signals=signals[:30],
                        duration_ms=int((time.time() - start_time) * 1000),
                        note="Direct SERP scrape blocked (/sorry/). Autocomplete signals preserved.",
                    )
            finally:
                await page.close()

        duration_ms = int((time.time() - start_time) * 1000)
        status = "ok" if len(all_suggestions) >= 3 else ("partial" if all_suggestions else "error")

        return SourceResult(
            source_id="google",
            status=status,
            strategy_used="suggest_endpoint",
            suggestions=all_suggestions[:30],
            related_searches=related_searches[:10],
            signals=signals[:30],
            duration_ms=duration_ms,
        )


scrape_google = GoogleSignalsAdapter().search
