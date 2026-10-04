import asyncio
import re
import urllib.parse

import httpx
from backend.app.config import get_settings
from backend.app.schemas import SocialSignal

WISH_PATTERNS = [
    re.compile(
        r"(?:looking for|where to buy|any recommendation for|recommend(?:ation)? for|suggest(?:ion)? for)\s+([a-zA-Z0-9\s-]{3,35})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d{3}\s*gsm\b|french terry|heavyweight cotton|acid wash|boxy fit|oversized fit)",
        re.IGNORECASE,
    ),
]


async def scrape_reddit(queries: list[str]) -> list[SocialSignal]:
    """
    Scrapes Reddit fashion communities using public JSON endpoints.
    Caps total requests to 12 per run with 6s politeness delay.
    """
    settings = get_settings()
    subreddits = settings.parsed_reddit_subreddits
    headers = {"User-Agent": "marketplace-keyword-agent/0.1 (by local-user)"}

    signals_map: dict[str, dict] = {}
    request_count = 0
    max_requests = 12

    async with httpx.AsyncClient(headers=headers, timeout=12.0) as client:
        for query in queries:
            if request_count >= max_requests:
                break

            encoded = urllib.parse.quote_plus(query)

            # 1. Target subreddits first
            for sub in subreddits:
                if request_count >= max_requests:
                    break

                url = f"https://www.reddit.com/r/{sub}/search.json?q={encoded}&restrict_sr=1&limit=25&sort=relevance&t=year"
                try:
                    request_count += 1
                    resp = await client.get(url)
                    if resp.status_code == 403:
                        # Reddit blocked public search access
                        break
                    elif resp.status_code == 200:
                        posts = resp.json().get("data", {}).get("children", [])
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
                                                "sample_titles": [],
                                            }
                                        signals_map[phrase]["mentions"] += 1
                                        if title and len(signals_map[phrase]["sample_titles"]) < 3:
                                            signals_map[phrase]["sample_titles"].append(title[:80])

                    # Sleep between calls to respect Reddit public rate limits
                    await asyncio.sleep(2.0)

                except Exception:
                    continue

    signals = [
        SocialSignal(
            source="reddit",
            phrase=v["phrase"],
            mentions=v["mentions"],
            sample_titles=v["sample_titles"],
        )
        for v in signals_map.values()
    ]
    signals.sort(key=lambda s: s.mentions, reverse=True)
    return signals[:40]
