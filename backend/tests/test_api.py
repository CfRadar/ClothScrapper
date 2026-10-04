import os

import httpx
import pytest
import pytest_asyncio
from backend.app.agents.analyst import AnalystAgent, AnalystOutputSchema
from backend.app.agents.marketplace_scraper import MarketplaceScraperAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.social_scraper import SocialScraperAgent
from backend.app.db import init_db
from backend.app.main import app
from backend.app.orchestrator import WorkflowOrchestrator
from backend.app.routers import runs as runs_router
from backend.app.schemas import (
    OtherFactors,
    PlatformFactors,
    PlatformKeywords,
    SearchPlan,
    TargetMarket,
)
from backend.tests.test_agents import FakeLLMClient

TEST_DB_PATH = "backend/data/test_api.db"


@pytest_asyncio.fixture(autouse=True)
async def setup_api_test(monkeypatch):
    from backend.app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "DATABASE_PATH", TEST_DB_PATH)
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass
    await init_db(TEST_DB_PATH)
    yield
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_health_and_quota_endpoints():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Health
        h_resp = await client.get("/api/health")
        assert h_resp.status_code == 200
        assert h_resp.json()["ok"] is True

        # 2. Quota
        q_resp = await client.get("/api/quota")
        assert q_resp.status_code == 200
        q_data = q_resp.json()
        assert "remaining_today" in q_data
        assert "daily_limit" in q_data
        # Ensure secret is NEVER in quota output
        assert "sk-" not in str(q_data)


@pytest.mark.asyncio
async def test_pipeline_run_and_chat_mocked():
    # Setup mock responses for all agents
    mock_plan = SearchPlan(
        target_market=TargetMarket(
            age_range="18-30", personas=["Youth"], interests=[], regions=[], language_notes=""
        ),
        marketplace_queries={"amazon": ["oversized cotton t shirt"]},
        social_queries=["oversized streetwear tee"],
        seed_keywords=["oversized", "cotton"],
    )

    mock_analyst = AnalystOutputSchema(
        keywords=[
            PlatformKeywords(
                platform="amazon", keywords=["oversized cotton t-shirt", "drop shoulder black tee"]
            )
        ],
        other_factors=OtherFactors(
            target_market_summary="Metro Gen-Z",
            per_platform={
                "amazon": PlatformFactors(
                    title_formula="Brand + Fit + Tee",
                    recommended_title_example="Urban Oversized Tee",
                    attributes_to_fill=["Fit"],
                    price_band="₹499 - ₹799",
                    negative_keywords=["cheap"],
                    hashtags_or_tags=["#streetwear"],
                    competition_note="Moderate",
                    seasonality_note="Summer",
                )
            },
            general=["240 GSM heavy cotton"],
        ),
    )

    fake_llm = FakeLLMClient(
        responses={
            "planner": mock_plan,
            "social": {"candidate_keywords": ["oversized streetwear tee"]},
            "analyst": mock_analyst,
        }
    )

    # Inject mock orchestrator into runs_router
    runs_router.orchestrator_instance = WorkflowOrchestrator(
        llm_client=fake_llm,
        planner=PlannerAgent(llm_client=fake_llm),
        marketplace_scraper=MarketplaceScraperAgent(),
        social_scraper=SocialScraperAgent(llm_client=fake_llm),
        analyst=AnalystAgent(llm_client=fake_llm),
    )

    brief_payload = {
        "platforms": ["amazon"],
        "tshirt_type": "oversized graphic tee",
        "color": "black",
        "gender": "men",
        "fabric": "cotton",
    }

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create run
        res = await client.post("/api/runs", json=brief_payload)
        assert res.status_code == 201
        run_id = res.json()["run_id"]
        assert run_id

        # Query run
        run_data = await client.get(f"/api/runs/{run_id}")
        assert run_data.status_code == 200
