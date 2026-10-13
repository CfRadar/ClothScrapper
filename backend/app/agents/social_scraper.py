"""
Agent 3: Social & Search Signals Listener.
Gathers organic consumer demand, style trends, and search buzz from signal sources:
Google autocomplete, Pinterest style pins, Meta Ad Library copy, Reddit fashion communities, X, and Instagram.
Executes at most 1 LLM call per run to normalize colloquial phrases into candidate keywords.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine
from pydantic import BaseModel

from backend.app.config import get_settings
from backend.app.llm.client import LLMCallError, OpenRouterClient, QuotaExceeded
from backend.app.schemas import SearchPlan, SocialScrape, SocialSignal
from backend.app.scrapers.adapters import get_adapter
from backend.app.scrapers.base import SourceResult
from backend.app.scrapers.health import record_health
from backend.app.scrapers.registry import get_source_spec

logger = logging.getLogger("backend.agents.social_scraper")

SYSTEM_PROMPT = """You turn raw search autocomplete and social phrases into shopper search keywords for T-shirts on Indian marketplaces.
Keep only phrases that describe a product, style, fit, color, fabric, design, trend, wholesale attribute, or occasion.
Drop usernames, profanity, brand/celebrity names, and anything unrelated to apparel.
Return JSON: {"candidate_keywords": ["..."]} with at most 30 short lowercase keywords."""


class SocialKeywordExtraction(BaseModel):
    candidate_keywords: list[str]


class SocialScraperAgent:
    """Agent 3: Gathers social & search signals; uses at most 1 LLM call to normalize phrases."""

    def __init__(self, llm_client: OpenRouterClient):
        self.llm = llm_client

    async def run(
        self,
        plan: SearchPlan,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
        emit_node: Callable[[str, str, str | None, dict | None], Coroutine[Any, Any, None]] | None = None,
        research_sources: list[str] | None = None,
    ) -> SocialScrape:
        if emit_node:
            await emit_node("social", "running", "Gathering search and social signals", None)

        await emit(
            "stage",
            "social",
            "Gathering search and social listening signals from demand sources...",
            None,
        )

        queries = plan.social_queries or ["oversized t-shirt", "cotton streetwear tee"]
        primary_query = queries[0]

        # Determine signal sources to run
        active_sources = research_sources or ["google", "pinterest", "reddit"]
        # Always check best-effort sources if enabled in settings
        settings = get_settings()
        if settings.ENABLE_X and "x" not in active_sources:
            active_sources.append("x")
        if settings.ENABLE_INSTAGRAM and "instagram" not in active_sources:
            active_sources.append("instagram")

        all_signals: list[SocialSignal] = []
        statuses: dict[str, str] = {}

        for src_id in active_sources:
            spec = get_source_spec(src_id)
            if emit_node:
                await emit_node(src_id, "running", f"Querying {spec.label if spec else src_id}", None)

            adapter = get_adapter(src_id)
            try:
                res: SourceResult = await adapter.search(primary_query)
                statuses[src_id] = res.status

                # Map signals
                src_sigs = [
                    SocialSignal(
                        source=s.source,
                        phrase=s.phrase,
                        mentions=s.mentions,
                        sample_titles=s.samples,
                    )
                    for s in res.signals
                ]
                all_signals.extend(src_sigs)

                # Update health in SQLite
                await record_health(
                    source_id=src_id,
                    result_status=res.status,
                    strategy_used=res.strategy_used,
                    failure_cause=res.cause or (res.note if res.status not in ("ok", "partial") else None),
                    status_override=spec.status_override if spec else None,
                )

                if emit_node:
                    metrics = {
                        "signals": len(src_sigs),
                        "duration_ms": res.duration_ms,
                        "strategy": res.strategy_used or "none",
                    }
                    if res.status in ("ok", "partial"):
                        await emit_node(src_id, "success", f"{len(src_sigs)} signals gathered", metrics)
                    elif res.status == "skipped":
                        await emit_node(src_id, "skipped", res.note or "Source disabled", metrics)
                    elif res.status == "blocked":
                        await emit_node(src_id, "warning", res.note or "Access blocked", metrics)
                    else:
                        await emit_node(src_id, "error", res.note or "Error querying source", metrics)

            except Exception as e:
                logger.warning(f"Error querying signal source {src_id}: {e}")
                statuses[src_id] = "error"
                if emit_node:
                    await emit_node(src_id, "error", f"Error: {e}", None)

        # Deduplicate signals by phrase
        phrase_counts: dict[str, int] = {}
        for s in all_signals:
            phrase_counts[s.phrase] = phrase_counts.get(s.phrase, 0) + s.mentions

        top_phrases = sorted(phrase_counts.keys(), key=lambda p: phrase_counts[p], reverse=True)[
            :60
        ]

        candidate_keywords: list[str] = []

        if top_phrases:
            # At most 1 LLM call to cluster and normalize into shopper keywords
            await emit(
                "progress",
                "social",
                "Normalizing search and community buzz into shopper search terms...",
                None,
            )
            user_prompt = f"Raw demand and search phrases from Indian shoppers:\n{top_phrases}"

            try:
                result: SocialKeywordExtraction = await self.llm.chat(
                    role="social",
                    system=SYSTEM_PROMPT,
                    user=user_prompt,
                    schema=SocialKeywordExtraction,
                    max_tokens=800,
                    temperature=0.2,
                )
                candidate_keywords = [
                    k.lower().strip()
                    for k in result.candidate_keywords
                    if k and len(k.strip()) >= 3
                ][:30]
            except (QuotaExceeded, LLMCallError) as err:
                logger.warning(
                    f"Social LLM normalization failed or skipped ({err}). Falling back to raw top phrases."
                )
                candidate_keywords = top_phrases[:25]
        else:
            candidate_keywords = []

        if emit_node:
            await emit_node(
                "social",
                "success",
                f"{len(candidate_keywords)} candidate buzzwords",
                {"signals": len(all_signals), "keywords": len(candidate_keywords)},
            )

        await emit(
            "progress",
            "social",
            f"Demand signals collection complete ({len(candidate_keywords)} keywords identified).",
            None,
        )

        return SocialScrape(
            signals=all_signals,
            statuses=statuses,
            candidate_keywords=candidate_keywords,
        )
