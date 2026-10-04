import logging
from typing import Any, Callable, Coroutine

from backend.app.config import get_settings
from backend.app.llm.client import LLMCallError, OpenRouterClient, QuotaExceeded
from backend.app.schemas import PlatformName, ProductBrief, SearchPlan, TargetMarket

logger = logging.getLogger("backend.agents.planner")

SYSTEM_PROMPT_TEMPLATE = """You are an e-commerce market analyst for Indian fashion marketplaces.
Given a T-shirt brief, infer the target market and produce search queries
that a real Indian shopper would type on Amazon.in, Myntra and Flipkart.
Rules:
- Queries must be 2-6 words, lowercase, realistic shopper language (include Hinglish only if natural).
- Max {MAX_QUERIES_PER_PLATFORM} queries per requested platform, no duplicates, mix: 1 broad, 2 specific (type+color / fit), 1-2 long-tail (occasion/design).
- Max 5 social queries (for Reddit/X/Instagram discussions and hashtags).
- seed_keywords: 10-20 core terms from the brief.
- Do not invent facts about the product. Do not use brand/celebrity names unless given in the brief.
Return JSON matching the schema."""


class PlannerAgent:
    """Agent 1: Incurs at most 1 LLM call to generate search queries and target market."""

    def __init__(self, llm_client: OpenRouterClient):
        self.llm = llm_client

    def _build_deterministic_fallback(self, brief: ProductBrief) -> SearchPlan:
        """Deterministic fallback search plan when quota is out or LLM fails."""
        settings = get_settings()
        target = TargetMarket(
            age_range="18-30",
            personas=["College Students", "Young Working Professionals", "Streetwear Enthusiasts"],
            interests=["Casual fashion", "Streetwear", "Comfort wear", "Minimalist aesthetic"],
            regions=["Metro & Tier-1/2 Indian Cities"],
            language_notes="Shoppers use terms like 'cotton oversized tee', 'baggy t shirt', 'loose fit round neck'.",
        )

        t_type = brief.tshirt_type.lower()
        color = brief.color.lower()
        gender = brief.gender.lower()

        queries_map: dict[PlatformName, list[str]] = {}
        for p in brief.platforms:
            q_list = [
                f"{color} {t_type}",
                f"{gender} {color} {t_type}",
                f"{t_type} for {gender}",
                f"casual {color} {t_type}",
                f"{color} {t_type} cotton",
            ]
            queries_map[p] = q_list[: settings.MAX_QUERIES_PER_PLATFORM]

        social_q = [
            f"{color} {t_type}",
            f"{t_type} recommendation",
            f"best {t_type} india",
            f"where to buy {t_type}",
        ]

        seeds = [t_type, color, gender, "cotton", "t-shirt", "round neck", "casual", "oversized"]
        return SearchPlan(
            target_market=target,
            marketplace_queries=queries_map,
            social_queries=social_q[:5],
            seed_keywords=seeds,
        )

    async def run(
        self,
        brief: ProductBrief,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> SearchPlan:
        await emit("stage", "planner", "AI Planner analyzing brief and target market...", None)
        settings = get_settings()

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            MAX_QUERIES_PER_PLATFORM=settings.MAX_QUERIES_PER_PLATFORM
        )

        user_prompt = f"Product Brief:\n{brief.model_dump_json(indent=2)}"

        try:
            plan: SearchPlan = await self.llm.chat(
                role="planner", system=system_prompt, user=user_prompt, schema=SearchPlan
            )
            await emit(
                "progress",
                "planner",
                "Search queries and target market generated successfully.",
                None,
            )
        except (QuotaExceeded, LLMCallError) as e:
            logger.warning(
                f"Planner LLM failed or quota exceeded ({e}). Using deterministic fallback plan."
            )
            await emit("warning", "planner", f"Planner fallback active: {e}", None)
            plan = self._build_deterministic_fallback(brief)

        # Code-level sanitation: dedupe, lowercase, trim queries to MAX_QUERIES_PER_PLATFORM
        sanitized_queries: dict[PlatformName, list[str]] = {}
        for p in brief.platforms:
            raw_list = plan.marketplace_queries.get(p, [])
            clean_list = []
            for q in raw_list:
                norm_q = q.lower().strip()
                if norm_q and norm_q not in clean_list:
                    clean_list.append(norm_q)
            if not clean_list:
                clean_list = [f"{brief.color} {brief.tshirt_type}".lower()]
            sanitized_queries[p] = clean_list[: settings.MAX_QUERIES_PER_PLATFORM]

        clean_social = []
        for sq in plan.social_queries:
            norm_sq = sq.lower().strip()
            if norm_sq and norm_sq not in clean_social:
                clean_social.append(norm_sq)

        plan.marketplace_queries = sanitized_queries
        plan.social_queries = clean_social[:5]
        return plan

    _build_fallback_plan = _build_deterministic_fallback
