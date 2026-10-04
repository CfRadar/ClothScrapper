from typing import TypeVar

import pytest
from backend.app.agents.analyst import AnalystAgent, AnalystOutputSchema
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.social_scraper import SocialScraperAgent
from backend.app.config import Settings
from backend.app.llm.client import OpenRouterClient
from backend.app.schemas import (
    ChatResponse,
    OtherFactors,
    PlatformFactors,
    PlatformKeywords,
    ProductBrief,
    SearchPlan,
    TargetMarket,
)
from pydantic import BaseModel, SecretStr

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient(OpenRouterClient):
    """Mock LLM client that returns predefined schema objects and tracks calls."""

    def __init__(self, responses: dict):
        settings = Settings(OPENROUTER_API_KEY=SecretStr("sk-fake-key"))
        super().__init__(settings=settings)
        self.responses = responses
        self.call_history = []

    async def chat(
        self,
        *,
        role: str,
        system: str,
        user: str,
        schema: type[T] | None = None,
        max_tokens: int = 2500,
        temperature: float = 0.3,
    ) -> T:
        self.llm_calls_used += 1
        self.call_history.append((role, user))

        resp_obj = self.responses.get(role)
        if isinstance(resp_obj, Exception):
            raise resp_obj
        if schema and isinstance(resp_obj, schema):
            return resp_obj
        if schema and isinstance(resp_obj, dict):
            return schema.model_validate(resp_obj)
        return resp_obj


async def dummy_emit(event_type: str, stage: str, message: str, data=None):
    pass


@pytest.mark.asyncio
async def test_planner_agent():
    mock_plan = SearchPlan(
        target_market=TargetMarket(
            age_range="18-25",
            personas=["Gen Z"],
            interests=["Streetwear"],
            regions=["Delhi", "Mumbai"],
            language_notes="Oversized loose fit",
        ),
        marketplace_queries={"amazon": ["oversized black t shirt", "cotton tee"]},
        social_queries=["oversized tee streetwear"],
        seed_keywords=["black", "oversized", "tee"],
    )

    fake_llm = FakeLLMClient(responses={"planner": mock_plan})
    planner = PlannerAgent(llm_client=fake_llm)

    brief = ProductBrief(platforms=["amazon"], tshirt_type="oversized tee", color="black")
    plan = await planner.run(brief, dummy_emit)

    assert plan.target_market.age_range == "18-25"
    assert "amazon" in plan.marketplace_queries
    assert fake_llm.llm_calls_used == 1


@pytest.mark.asyncio
async def test_social_scraper_agent():
    fake_llm = FakeLLMClient(
        responses={"social": {"candidate_keywords": ["oversized tee", "drop shoulder cotton"]}}
    )
    social_agent = SocialScraperAgent(llm_client=fake_llm)

    plan = SearchPlan(
        target_market=TargetMarket(
            age_range="20-30", personas=[], interests=[], regions=[], language_notes=""
        ),
        marketplace_queries={},
        social_queries=["oversized tee"],
        seed_keywords=[],
    )

    result = await social_agent.run(plan, dummy_emit)
    assert result.statuses["reddit"] in ("ok", "skipped")
    assert fake_llm.llm_calls_used <= 1


@pytest.mark.asyncio
async def test_analyst_agent_and_chat():
    mock_analyst = AnalystOutputSchema(
        keywords=[
            PlatformKeywords(
                platform="amazon", keywords=["oversized black tee", "cotton drop shoulder"]
            )
        ],
        other_factors=OtherFactors(
            target_market_summary="College youth",
            per_platform={
                "amazon": PlatformFactors(
                    title_formula="Brand + Fit + Color + Tee",
                    recommended_title_example="Demo Title",
                    attributes_to_fill=["Fit", "Fabric"],
                    price_band="₹499 - ₹799",
                    negative_keywords=["cheap"],
                    hashtags_or_tags=["#streetwear"],
                    competition_note="Medium",
                    seasonality_note="Year round",
                )
            },
            general=["Focus on 240 GSM"],
        ),
    )

    mock_chat = ChatResponse(
        reply="Updated keywords for Amazon.",
        keywords_patch=[
            PlatformKeywords(platform="amazon", keywords=["gen-z oversized black tee"])
        ],
    )

    fake_llm = FakeLLMClient(responses={"analyst": mock_analyst})
    analyst = AnalystAgent(llm_client=fake_llm)

    brief = ProductBrief(platforms=["amazon"], tshirt_type="oversized tee", color="black")
    plan = SearchPlan(
        target_market=TargetMarket(
            age_range="18-25", personas=[], interests=[], regions=[], language_notes=""
        ),
        marketplace_queries={"amazon": ["oversized tee"]},
        social_queries=[],
        seed_keywords=[],
    )

    run_res = await analyst.run(
        brief=brief,
        plan=plan,
        scored_candidates={"amazon": [("oversized black tee", 0.9)]},
        marketplace_scrapes={},
        social_scrape=None,
        emit=dummy_emit,
    )

    assert len(run_res.keywords) == 1
    assert run_res.keywords[0].platform == "amazon"
    assert run_res.keywords[0].keywords[0] == "oversized black tee"

    # Test Chat
    fake_llm.responses["analyst"] = mock_chat
    chat_res = await analyst.chat(run_res, "Make it more Gen-Z")
    assert chat_res.reply == "Updated keywords for Amazon."
    assert chat_res.keywords_patch is not None
    assert chat_res.keywords_patch[0].keywords == ["gen-z oversized black tee"]
