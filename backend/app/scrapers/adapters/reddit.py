"""
Reddit Social Listening Adapter.
Conforms to SourceAdapter Protocol.
Extracts shopper signals, wish patterns, and fabric buzz from Reddit fashion communities.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
from typing import Any

from backend.app.config import get_settings
from backend.app.net.safe_http import SafeAsyncClient
from backend.app.scrapers.base import BaseSourceAdapter, SocialSignal, SourceResult

logger = logging.getLogger("backend.scrapers.adapters.reddit")

WISH_PATTERNS = [
    re.compile(
        r"(?:looking for|where to buy|any recommendation for|recommend(?:ation)? for|suggest(?:ion)? for)\s+([a-zA-Z0-9\s-]{3,35})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{3}\s*gsm\b|french terry|heavyweight cotton|acid wash|boxy fit|oversized fit|drop shoulder)",
        re.IGNORECASE,
    ),
]


class RedditAdapter(BaseSourceAdapter):
    def __init__(self):
        super().__init__(
            source_id="reddit",
            group="Search and social",
            kind="social",
            roles=["signal"],
        )

    def parse(self, raw: str | dict[str, Any]) -> list[SocialSignal]:
        """Pure parser function extracting SocialSignal models from Reddit search JSON."""
        data = raw if isinstance(raw, dict) else {}
        signals_map: dict[str, dict] = {}
        posts = data.get("data", {}).get("children", [])

        for p in posts:
            p_data = p.get("data", {})
            title = p_data.get("title", "")
            selftext = p_data.get("selftext", "")
            text = f"{title} {selftext}"

            for pat in WISH_PATTERNS:
                for match in pat.findall(text):
                    phrase = match.strip().lower()
                    if len(phrase) >= 3 and not phrase.isdigit():
                        if phrase not in signals_map:
                            signals_map[phrase] = {
                                "source": "reddit",
                                "phrase": phrase,
                                "mentions": 0,
                                "samples": [],
                            }
                        signals_map[phrase]["mentions"] += 1
                        if title and len(signals_map[phrase]["samples"]) < 3:
                            signals_map[phrase]["samples"].append(title[:80])

        signals = [
            SocialSignal(
                source="reddit",
                phrase=v["phrase"],
                mentions=v["mentions"],
                samples=v["samples"],
            )
            for v in signals_map.values()
        ]
        signals.sort(key=lambda s: s.mentions, reverse=True)
        return signals

    _blocked_until: float = 0.0

    async def search(self, query: str, ctx: Any = None) -> SourceResult:
        start_time = time.time()

        # Fast circuit-breaker return if platform recently restricted access
        if time.time() < self._blocked_until:
            return SourceResult(
                source_id="reddit",
                status="blocked",
                cause="blocked",
                signals=[],
                duration_ms=0,
                note="Reddit circuit breaker active (unauthenticated requests restricted).",
            )

        settings = get_settings()
        subreddits = settings.parsed_reddit_subreddits or ["IndianFashionAddicts", "streetwearstartup"]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        all_signals: list[SocialSignal] = []
        encoded = urllib.parse.quote_plus(query)
        is_blocked = False

        async with SafeAsyncClient(headers=headers, timeout=10.0) as client:
            for sub in subreddits[:3]:  # Limit to top 3 subreddits
                url = f"https://www.reddit.com/r/{sub}/search.json?q={encoded}&restrict_sr=1&limit=25&sort=relevance&t=year"
                try:
                    resp = await client.get(url)
                    if resp.status_code in (403, 429):
                        is_blocked = True
                        RedditAdapter._blocked_until = time.time() + 1800.0  # 30 min circuit breaker
                        logger.info(f"Reddit search returned HTTP {resp.status_code} (access restricted). Circuit breaker set for 30m.")
                        break
                    elif resp.status_code == 200:
                        parsed = self.parse(resp.json())
                        all_signals.extend(parsed)

                    await asyncio.sleep(1.0)  # Politeness interval
                except Exception as e:
                    logger.debug(f"Error querying Reddit r/{sub}: {e}")
                    continue

        duration_ms = int((time.time() - start_time) * 1000)

        if is_blocked and not all_signals:
            return SourceResult(
                source_id="reddit",
                status="blocked",
                cause="blocked",
                signals=[],
                duration_ms=duration_ms,
                note="Reddit unauthenticated search restricted by platform policy.",
            )

        status = "ok" if len(all_signals) >= 3 else ("partial" if all_signals else "error")
        return SourceResult(
            source_id="reddit",
            status=status,
            strategy_used="suggest_endpoint",
            cause=None if status == "ok" else "rate_limited",
            signals=all_signals[:40],
            duration_ms=duration_ms,
        )


scrape_reddit = RedditAdapter().search
