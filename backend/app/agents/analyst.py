import json
import logging
from statistics import median
from typing import Any, Callable, Coroutine

from backend.app.llm.client import LLMCallError, OpenRouterClient, QuotaExceeded
from backend.app.schemas import (
    ChatResponse,
    OtherFactors,
    PlatformFactors,
    PlatformKeywords,
    PlatformName,
    PlatformScrape,
    ProductBrief,
    RunResult,
    SearchPlan,
    SocialScrape,
)
from pydantic import BaseModel, field_validator

logger = logging.getLogger("backend.agents.analyst")

SYSTEM_PROMPT = """You are a marketplace SEO analyst for Indian T-shirt sellers.
You receive pre-scored keyword candidates per platform, real product statistics, and social signals.
Produce:
1) keywords: for EACH requested platform, 15-25 final keywords ordered best-first.
   - Only keywords. No explanations, no numbering, no brand/celebrity names, no duplicates across the same platform.
   - Choose only from or lightly recombine the provided candidates; prefer high-score, high-relevance terms matching the brief.
   - Respect platform style: Amazon = search-style phrases; Myntra = attribute-style phrases (fit, neck, occasion, pattern); Flipkart = title-style phrases.
2) other_factors: target_market_summary, per-platform title_formula, recommended_title_example,
   attributes_to_fill, price_band (from provided stats), negative_keywords, hashtags_or_tags,
   competition_note, seasonality_note, plus general cross-platform notes.
Never invent numbers; only use statistics provided. Return a single JSON object matching the schema."""

CHAT_SYSTEM_PROMPT = """You are an expert e-commerce SEO consultant assisting an Indian T-shirt seller.
Below is the seller's current run result including platform keywords and other factors.
Answer the seller's question concisely.
If they ask to change keywords (e.g. more Gen-Z, remove a word, focus on one platform, add Hindi/Hinglish, shorter), return a keywords_patch with the complete updated list of 15-25 keywords for only the affected platforms.
Otherwise return reply only.
Return a valid JSON object matching ChatResponse schema:
{"reply": "...", "keywords_patch": [{"platform": "amazon", "keywords": [...]}]}"""


class AnalystOutputSchema(BaseModel):
    keywords: list[PlatformKeywords]
    other_factors: OtherFactors

    @field_validator("keywords", mode="before")
    @classmethod
    def coerce_keywords(cls, val: Any) -> Any:
        if isinstance(val, dict):
            return [
                PlatformKeywords(platform=k, keywords=v if isinstance(v, list) else [str(v)])
                for k, v in val.items()
            ]
        return val


def calculate_platform_stats(scrape: PlatformScrape | None) -> dict[str, Any]:
    if not scrape or not scrape.products:
        return {
            "total_products": 0,
            "median_price": None,
            "price_quartiles": None,
            "pct_sponsored": 0,
            "top_brands": [],
        }

    prices = sorted([p.price for p in scrape.products if p.price is not None and p.price > 0])
    sponsored_count = sum(1 for p in scrape.products if p.sponsored)
    brands = [p.brand for p in scrape.products if p.brand]

    med_price = round(median(prices), 2) if prices else 499.0
    q1 = round(prices[len(prices) // 4], 2) if len(prices) >= 4 else med_price
    q3 = round(prices[(3 * len(prices)) // 4], 2) if len(prices) >= 4 else med_price

    brand_counts: dict[str, int] = {}
    for b in brands:
        brand_counts[b] = brand_counts.get(b, 0) + 1
    top_brands = sorted(brand_counts.keys(), key=lambda b: brand_counts[b], reverse=True)[:5]

    return {
        "total_products": len(scrape.products),
        "median_price": f"₹{med_price}",
        "price_quartiles": f"₹{q1} - ₹{q3}",
        "pct_sponsored": f"{round((sponsored_count / len(scrape.products)) * 100, 1)}%",
        "top_brands": top_brands,
    }


class AnalystAgent:
    """Agent 4: Curates final platform keywords and other factors; powers interactive chat."""

    def __init__(self, llm_client: OpenRouterClient):
        self.llm = llm_client

    def _build_deterministic_fallback(
        self,
        brief: ProductBrief,
        plan: SearchPlan,
        scored_candidates: dict[PlatformName, list[tuple[str, float]]],
        marketplace_scrapes: dict[PlatformName, PlatformScrape],
    ) -> AnalystOutputSchema:
        """Deterministic fallback synthesis if LLM calls are exhausted."""
        keywords_list = []
        per_platform_factors = {}

        for p in brief.platforms:
            cands = scored_candidates.get(p, [])
            top_kw = [c[0] for c in cands[:20]]
            if len(top_kw) < 15:
                # Add default fallbacks
                top_kw.extend(
                    [
                        f"{brief.color} {brief.tshirt_type}",
                        f"cotton {brief.tshirt_type}",
                        "casual streetwear tee",
                    ]
                )
            keywords_list.append(PlatformKeywords(platform=p, keywords=top_kw[:25]))

            stats = calculate_platform_stats(marketplace_scrapes.get(p))
            per_platform_factors[p] = PlatformFactors(
                title_formula="[Brand] + [Fit] + [Neck/Style] + [Color] + [Fabric] + T-Shirt",
                recommended_title_example=f"UrbanStyle Men {brief.fit or 'Oversized'} Round Neck {brief.color} Pure Cotton T-Shirt",
                attributes_to_fill=[
                    "Fit",
                    "Fabric",
                    "Neck Type",
                    "Sleeve Length",
                    "Occasion",
                    "Color",
                ],
                price_band=stats.get("price_quartiles") or "₹499 - ₹899",
                negative_keywords=["cheap", "free", "fake", "replica", "combo"],
                hashtags_or_tags=["streetwear", "oversized", "cotton", "casualwear"],
                competition_note=f"High competition from top brands: {', '.join(stats.get('top_brands', []) or ['Market leaders'])}",
                seasonality_note="Peak demand during summer and festive college season.",
            )

        target_summary = (
            f"Targeting shoppers looking for {brief.color} {brief.tshirt_type}. "
            f"Primary audience: {plan.target_market.age_range} in metro cities."
        )

        return AnalystOutputSchema(
            keywords=keywords_list,
            other_factors=OtherFactors(
                target_market_summary=target_summary,
                per_platform=per_platform_factors,
                general=[
                    "Maintain minimum 220 GSM for oversized streetwear positioning.",
                    "Ensure high-resolution lookbook images highlighting drop shoulder drape.",
                    "Keep backend search terms free of punctuation and duplicate words.",
                ],
            ),
        )

    async def run(
        self,
        brief: ProductBrief,
        plan: SearchPlan,
        scored_candidates: dict[PlatformName, list[tuple[str, float]]],
        marketplace_scrapes: dict[PlatformName, PlatformScrape],
        social_scrape: SocialScrape | None,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> RunResult:
        await emit(
            "stage",
            "analyst",
            "AI Analyst synthesizing final keywords and strategic factors...",
            None,
        )

        # Compute product statistics per platform
        platform_stats = {
            p: calculate_platform_stats(marketplace_scrapes.get(p)) for p in brief.platforms
        }

        # Truncate candidates to top 40 strings for prompt budget
        prompt_candidates = {
            p: [c[0] for c in scored_candidates.get(p, [])[:40]] for p in brief.platforms
        }

        user_prompt = json.dumps(
            {
                "brief": brief.model_dump(),
                "target_market": plan.target_market.model_dump(),
                "scored_candidates": prompt_candidates,
                "social_signals": (social_scrape.candidate_keywords if social_scrape else [])[:20],
                "platform_stats": platform_stats,
            },
            indent=2,
        )

        try:
            analysis_output: AnalystOutputSchema = await self.llm.chat(
                role="analyst",
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=AnalystOutputSchema,
                max_tokens=3000,
                temperature=0.25,
            )
        except (QuotaExceeded, LLMCallError) as err:
            logger.warning(
                f"Analyst LLM failed or quota exceeded ({err}). Using deterministic synthesis fallback."
            )
            await emit("warning", "analyst", f"Analyst fallback active: {err}", None)
            analysis_output = self._build_deterministic_fallback(
                brief, plan, scored_candidates, marketplace_scrapes
            )

        platform_statuses = {
            p: (marketplace_scrapes[p].status if p in marketplace_scrapes else "skipped")
            for p in brief.platforms
        }

        await emit(
            "progress",
            "analyst",
            "Final keywords and other factors synthesized successfully.",
            None,
        )

        return RunResult(
            run_id="",  # Assigned by orchestrator
            keywords=analysis_output.keywords,
            other_factors=analysis_output.other_factors,
            platform_statuses=platform_statuses,
            llm_calls_used=self.llm.llm_calls_used,
        )

    async def chat(
        self,
        current_result: RunResult,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResponse:
        """Interactive chat with the AI Analyst to customize keywords or answer questions."""
        # Cap result context
        compact_result = json.dumps(current_result.model_dump(), separators=(",", ":"))
        if len(compact_result) > 6000:
            compact_result = compact_result[:6000] + "...}"

        history_context = ""
        if history:
            # Last 6 messages
            recent = history[-6:]
            history_context = "\nRecent Conversation:\n" + "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent
            )

        user_prompt = (
            f"Current Result Data:\n{compact_result}\n{history_context}\nUser Message: {message}"
        )

        try:
            response: ChatResponse = await self.llm.chat(
                role="analyst",
                system=CHAT_SYSTEM_PROMPT,
                user=user_prompt,
                schema=ChatResponse,
                max_tokens=1500,
                temperature=0.3,
            )
            return response
        except (QuotaExceeded, LLMCallError) as err:
            return ChatResponse(
                reply=f"Unable to process request via AI: {err}. Please try again later.",
                keywords_patch=None,
                factors_patch=None,
            )
