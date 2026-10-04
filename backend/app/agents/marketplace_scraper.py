import asyncio
import logging
from typing import Any, Callable, Coroutine

from backend.app import cache
from backend.app.schemas import (
    PlatformName,
    PlatformScrape,
    ProductBrief,
    ScrapedProduct,
    SearchPlan,
)
from backend.app.scoring.candidates import normalize_text
from backend.app.scrapers import amazon, flipkart, myntra
from backend.app.scrapers.browser import BrowserManager

logger = logging.getLogger("backend.agents.marketplace_scraper")

PLATFORM_MODULES = {
    "amazon": amazon,
    "myntra": myntra,
    "flipkart": flipkart,
}


class MarketplaceScraperAgent:
    """Agent 2: Executes 0 LLM calls. Polite, cached marketplace scraping across platforms."""

    def __init__(self, browser_mgr: BrowserManager | None = None):
        self.browser_mgr = browser_mgr or BrowserManager.get_instance()

    async def _scrape_single_platform(
        self,
        platform: PlatformName,
        queries: list[str],
        plan: SearchPlan,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> PlatformScrape:
        """
        Executes queries for a single platform sequentially to enforce 1-page domain concurrency.
        Checks 24h SQLite cache first. Stops if blocked.
        """
        scraper_mod = PLATFORM_MODULES.get(platform)
        if not scraper_mod:
            return PlatformScrape(
                platform=platform, status="error", note=f"Unknown platform: {platform}"
            )

        all_products: list[ScrapedProduct] = []
        all_suggestions: list[str] = []
        all_related: list[str] = []
        platform_status = "ok"
        stop_reason = None

        total_queries = len(queries)

        for idx, q in enumerate(queries, 1):
            norm_q = normalize_text(q).replace(" ", "_")
            cache_key = f"scrape:{platform}:{norm_q}"

            # 1. Check Cache
            cached_data = await cache.get(cache_key)
            if cached_data:
                await emit(
                    "progress",
                    "marketplace",
                    f"{platform}: query {idx}/{total_queries} loaded from 24h cache.",
                    None,
                )
                try:
                    c_scrape = PlatformScrape.model_validate(cached_data)
                    all_products.extend(c_scrape.products)
                    all_suggestions.extend(c_scrape.suggestions)
                    all_related.extend(c_scrape.related_searches)
                    continue
                except Exception:
                    pass

            # 2. Live Scrape
            await emit(
                "progress",
                "marketplace",
                f"{platform}: executing query {idx}/{total_queries} ('{q}')...",
                None,
            )
            scrape_res: PlatformScrape = await scraper_mod.search(q, plan, self.browser_mgr)

            if scrape_res.status == "blocked":
                platform_status = "blocked"
                stop_reason = scrape_res.note or "Bot challenge / CAPTCHA detected."
                await emit(
                    "warning",
                    "marketplace",
                    f"{platform} blocked further access. Continuing with available signals.",
                    None,
                )
                all_suggestions.extend(scrape_res.suggestions)
                break

            if scrape_res.status in ("ok", "partial"):
                all_products.extend(scrape_res.products)
                all_suggestions.extend(scrape_res.suggestions)
                all_related.extend(scrape_res.related_searches)
                await emit(
                    "progress",
                    "marketplace",
                    f"{platform}: query {idx}/{total_queries} done ({len(scrape_res.products)} products).",
                    None,
                )
                # Store in cache
                await cache.set(cache_key, scrape_res.model_dump())

        # Deduplicate products by URL or title
        deduped_products: list[ScrapedProduct] = []
        seen_titles = set()
        for p in all_products:
            norm_title = p.title.lower().strip()
            if norm_title not in seen_titles:
                seen_titles.add(norm_title)
                p.position = len(deduped_products) + 1
                deduped_products.append(p)

        # Deduplicate suggestions and related
        clean_sugg = list(dict.fromkeys(all_suggestions))
        clean_rel = list(dict.fromkeys(all_related))

        return PlatformScrape(
            platform=platform,
            status=platform_status,
            products=deduped_products,
            suggestions=clean_sugg,
            related_searches=clean_rel,
            note=stop_reason,
        )

    async def run(
        self,
        plan: SearchPlan,
        brief: ProductBrief,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> dict[PlatformName, PlatformScrape]:
        await emit("stage", "marketplace", "Gathering live marketplace search listings...", None)

        tasks = []
        for platform in brief.platforms:
            queries = plan.marketplace_queries.get(platform, [])
            tasks.append(self._scrape_single_platform(platform, queries, plan, emit))

        # Parallel across platforms, strictly sequential within each platform
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scrapes_map: dict[PlatformName, PlatformScrape] = {}
        for platform, res in zip(brief.platforms, results):
            if isinstance(res, Exception):
                logger.error(f"Platform {platform} scraping raised unhandled exception: {res}")
                scrapes_map[platform] = PlatformScrape(
                    platform=platform, status="error", products=[], note=str(res)
                )
            else:
                scrapes_map[platform] = res

        await emit("progress", "marketplace", "Marketplace data collection complete.", None)
        return scrapes_map
