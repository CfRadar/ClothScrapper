import asyncio
import logging
from typing import Any, Callable, Coroutine

from backend.app.llm.client import LLMCallError, OpenRouterClient, QuotaExceeded
from backend.app.schemas import SearchPlan, SocialScrape, SocialSignal
from backend.app.scrapers.instagram_best_effort import scrape_instagram_best_effort
from backend.app.scrapers.reddit import scrape_reddit
from backend.app.scrapers.x_best_effort import scrape_x_best_effort
from pydantic import BaseModel

logger = logging.getLogger("backend.agents.social_scraper")

SYSTEM_PROMPT = """You turn raw social-media phrases into shopper search keywords for T-shirts on Indian marketplaces.
Keep only phrases that describe a product, style, fit, color, fabric, design, trend or occasion.
Drop usernames, profanity, brand/celebrity names, and anything unrelated to apparel.
Return JSON: {"candidate_keywords": ["..."]} with at most 30 short lowercase keywords."""


class SocialKeywordExtraction(BaseModel):
    candidate_keywords: list[str]


class SocialScraperAgent:
    """Agent 3: Gathers social buzz; uses at most 1 LLM call to normalize colloquial phrases."""

    def __init__(self, llm_client: OpenRouterClient):
        self.llm = llm_client

    async def run(
        self,
        plan: SearchPlan,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> SocialScrape:
        await emit(
            "stage",
            "social",
            "Gathering social listening signals from fashion communities...",
            None,
        )

        queries = plan.social_queries or ["oversized t-shirt", "cotton streetwear tee"]

        # Run social sources
        reddit_task = scrape_reddit(queries)
        x_task = scrape_x_best_effort(queries)
        insta_task = scrape_instagram_best_effort(queries)

        reddit_signals, (x_status, x_signals), (insta_status, insta_signals) = await asyncio.gather(
            reddit_task, x_task, insta_task, return_exceptions=False
        )

        all_signals: list[SocialSignal] = []
        all_signals.extend(reddit_signals)
        all_signals.extend(x_signals)
        all_signals.extend(insta_signals)

        statuses = {
            "reddit": "ok" if reddit_signals else "skipped",
            "x": x_status,
            "instagram": insta_status,
        }

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
                "Normalizing community buzz into shopper search terms...",
                None,
            )
            user_prompt = f"Raw social phrases from Indian fashion communities:\n{top_phrases}"

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

        await emit(
            "progress",
            "social",
            f"Social listening complete ({len(candidate_keywords)} keywords identified).",
            None,
        )

        return SocialScrape(
            signals=all_signals,
            statuses=statuses,
            candidate_keywords=candidate_keywords,
        )
