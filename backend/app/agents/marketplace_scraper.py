"""
Agent 2: Marketplace, B2B, and Quick Commerce Scraper.
Runs all enabled sell-target sources through the registry-driven source adapter framework.
Enforces 0 LLM calls, 24h caching, per-domain locks, and circuit breaker skipping.
"""

from __future__ import annotations

import asyncio
import logging
import time
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
from backend.app.scrapers.adapters import get_adapter
from backend.app.scrapers.base import Item, SourceResult
from backend.app.scrapers.browser import BrowserManager
from backend.app.scrapers.health import is_circuit_breaker_open, record_health
from backend.app.scrapers.query_adapters import adapt_queries
from backend.app.scrapers.registry import get_source_spec

logger = logging.getLogger("backend.agents.marketplace_scraper")


class MarketplaceScraperAgent:
    """Agent 2: Executes 0 LLM calls. Registry-driven multi-source scraping."""

    def __init__(self, browser_mgr: BrowserManager | None = None):
        self.browser_mgr = browser_mgr or BrowserManager.get_instance()

    async def _scrape_single_platform(
        self,
        platform: PlatformName,
        queries: list[str],
        plan: SearchPlan,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
        emit_node: Callable[[str, str, str | None, dict | None], Coroutine[Any, Any, None]] | None = None,
    ) -> PlatformScrape:
        start_t = time.time()
        spec = get_source_spec(platform)

        # 1. Circuit breaker check
        if await is_circuit_breaker_open(platform):
            logger.warning(f"Circuit breaker is open for source '{platform}'. Skipping.")
            if emit_node:
                await emit_node(platform, "warning", "Source temporarily skipped after repeated failures", None)
            return PlatformScrape(
                platform=platform,
                status="skipped",
                note="Source temporarily skipped after repeated failures",
            )

        # 2. Unavailable / Disabled status check
        if spec and spec.status_override in ("unavailable", "disabled"):
            if emit_node:
                await emit_node(
                    platform,
                    "skipped",
                    spec.status_reason or f"Source {spec.status_override}",
                    None,
                )
            return PlatformScrape(
                platform=platform,
                status="unavailable" if spec.status_override == "unavailable" else "skipped",
                note=spec.status_reason,
            )

        if emit_node:
            await emit_node(platform, "running", f"Searching {platform}", None)

        adapter = get_adapter(platform)
        kind = spec.kind if spec else "marketplace"
        adapted_queries = adapt_queries(queries, kind)

        all_products: list[ScrapedProduct] = []
        all_suggestions: list[str] = []
        all_related: list[str] = []
        platform_status = "ok"
        stop_reason = None
        cache_hits = 0
        last_strategy = None
        last_cause = None

        total_queries = len(adapted_queries)

        for idx, q in enumerate(adapted_queries, 1):
            norm_q = normalize_text(q).replace(" ", "_")
            cache_key = f"scrape:{platform}:{norm_q}"

            # 1. Check Cache
            cached_data = await cache.get(cache_key)
            if cached_data:
                cache_hits += 1
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

            try:
                scrape_res: SourceResult = await adapter.search(q, self.browser_mgr)
                last_strategy = scrape_res.strategy_used
                last_cause = scrape_res.cause

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

                if scrape_res.status == "needs_location":
                    platform_status = "needs_location"
                    stop_reason = scrape_res.note or "Requires DELIVERY_PINCODE configuration."
                    await emit(
                        "warning",
                        "marketplace",
                        f"{platform} requires DELIVERY_PINCODE location setup.",
                        None,
                    )
                    break

                if scrape_res.status in ("ok", "partial"):
                    # Map Item models to ScrapedProduct
                    for it in scrape_res.items:
                        all_products.append(
                            ScrapedProduct(
                                platform=platform,
                                title=it.title,
                                brand=it.brand or (it.b2b.supplier if it.b2b else None),
                                price=it.price,
                                mrp=it.mrp,
                                rating=it.rating,
                                rating_count=it.rating_count,
                                position=it.position,
                                sponsored=it.sponsored,
                                url=it.url or "",
                            )
                        )
                    all_suggestions.extend(scrape_res.suggestions)
                    all_related.extend(scrape_res.related_searches)

                    await emit(
                        "progress",
                        "marketplace",
                        f"{platform}: query {idx}/{total_queries} done ({len(scrape_res.items)} items).",
                        None,
                    )

                    # Store in cache
                    serializable_scrape = PlatformScrape(
                        platform=platform,
                        status="ok",
                        products=[
                            ScrapedProduct(
                                platform=platform,
                                title=it.title,
                                brand=it.brand,
                                price=it.price,
                                mrp=it.mrp,
                                rating=it.rating,
                                rating_count=it.rating_count,
                                position=it.position,
                                sponsored=it.sponsored,
                                url=it.url or "",
                            )
                            for it in scrape_res.items
                        ],
                        suggestions=scrape_res.suggestions,
                        related_searches=scrape_res.related_searches,
                    )
                    await cache.set(cache_key, serializable_scrape.model_dump())

            except Exception as e:
                logger.warning(f"Error querying {platform} with '{q}': {e}")
                stop_reason = str(e)
                platform_status = "error"
                break

        # Record health after scrape run
        await record_health(
            source_id=platform,
            result_status=platform_status,
            strategy_used=last_strategy,
            failure_cause=last_cause or stop_reason,
            status_override=spec.status_override if spec else None,
        )

        # Deduplicate products by title
        deduped_products: list[ScrapedProduct] = []
        seen_titles = set()
        for p in all_products:
            norm_title = p.title.lower().strip()
            if norm_title not in seen_titles:
                seen_titles.add(norm_title)
                p.position = len(deduped_products) + 1
                deduped_products.append(p)

        clean_sugg = list(dict.fromkeys(all_suggestions))
        clean_rel = list(dict.fromkeys(all_related))
        duration_ms = round((time.time() - start_t) * 1000, 1)

        if emit_node:
            metrics = {
                "products": len(deduped_products),
                "queries": total_queries,
                "duration_ms": duration_ms,
                "strategy": last_strategy or "none",
                "cache_hit": 1 if cache_hits == total_queries and total_queries > 0 else 0,
            }
            if platform_status == "blocked":
                n_status = "warning"
                n_detail = f"Blocked after {len(deduped_products)} items"
            elif platform_status in ("error", "needs_location"):
                n_status = "warning" if platform_status == "needs_location" else "error"
                n_detail = stop_reason or "Error fetching products"
            elif cache_hits == total_queries and total_queries > 0:
                n_status = "cached"
                n_detail = f"{len(deduped_products)} products from cache"
            elif platform_status == "partial":
                n_status = "warning"
                n_detail = f"{len(deduped_products)} items (partial)"
            else:
                n_status = "success"
                n_detail = f"{len(deduped_products)} items from {total_queries} queries"
            await emit_node(platform, n_status, n_detail, metrics)

        return PlatformScrape(
            platform=platform,
            status=platform_status if platform_status in ("ok", "partial", "blocked", "error") else "error",
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
        emit_node: Callable[[str, str, str | None, dict | None], Coroutine[Any, Any, None]] | None = None,
    ) -> dict[PlatformName, PlatformScrape]:
        if emit_node:
            await emit_node("marketplace", "running", f"Scraping {', '.join(brief.platforms)}", None)
        await emit("stage", "marketplace", "Gathering live marketplace and wholesale listings...", None)

        # Priority ordering: high relevance first
        def get_priority(p: str) -> int:
            spec = get_source_spec(p)
            if not spec:
                return 99
            order = {"high": 0, "medium": 1, "low": 2, "none": 3, "unknown": 4}
            return order.get(spec.relevance, 2)

        ordered_platforms = sorted(brief.platforms, key=get_priority)

        tasks = []
        for platform in ordered_platforms:
            queries = plan.marketplace_queries.get(platform, plan.marketplace_queries.get("amazon", []))
            tasks.append(self._scrape_single_platform(platform, queries, plan, emit, emit_node))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        scrapes_map: dict[PlatformName, PlatformScrape] = {}
        for platform, res in zip(ordered_platforms, results):
            if isinstance(res, Exception):
                logger.error(f"Platform {platform} scraping raised unhandled exception: {res}")
                scrapes_map[platform] = PlatformScrape(
                    platform=platform, status="error", products=[], note=str(res)
                )
                if emit_node:
                    await emit_node(platform, "error", f"Error: {res}", None)
            else:
                scrapes_map[platform] = res

        total_prods = sum(len(s.products) for s in scrapes_map.values())
        has_issue = any(s.status in ("blocked", "error") for s in scrapes_map.values())
        if emit_node:
            mk_status = "warning" if has_issue else "success"
            await emit_node(
                "marketplace",
                mk_status,
                f"{total_prods} products gathered across {len(ordered_platforms)} platforms",
                {"products": total_prods},
            )

        await emit("progress", "marketplace", "Marketplace data collection complete.", None)
        return scrapes_map
