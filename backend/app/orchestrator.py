import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

from backend.app.agents.analyst import AnalystAgent
from backend.app.agents.marketplace_scraper import MarketplaceScraperAgent
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.social_scraper import SocialScraperAgent
from backend.app.db import get_db
from backend.app.llm.client import OpenRouterClient
from backend.app.schemas import (
    PlatformName,
    PlatformScrape,
    ProductBrief,
    RunResult,
    SearchPlan,
    SocialScrape,
)
from backend.app.scoring.scorer import score_all

logger = logging.getLogger("backend.orchestrator")


class WorkflowOrchestrator:
    """
    Coordinates the 4-agent pipeline using plain asyncio workflows:
    Planner (Agent 1) -> (Marketplace Scraper [Agent 2] || Social Scraper [Agent 3]) -> Scoring -> Analyst (Agent 4).
    Strictly enforces <= 4 LLM calls and per-stage timeouts.
    """

    def __init__(
        self,
        llm_client: OpenRouterClient | None = None,
        planner: PlannerAgent | None = None,
        marketplace_scraper: MarketplaceScraperAgent | None = None,
        social_scraper: SocialScraperAgent | None = None,
        analyst: AnalystAgent | None = None,
    ):
        self.llm = llm_client or OpenRouterClient()
        self.planner = planner or PlannerAgent(llm_client=self.llm)
        self.marketplace_scraper = marketplace_scraper or MarketplaceScraperAgent()
        self.social_scraper = social_scraper or SocialScraperAgent(llm_client=self.llm)
        self.analyst = analyst or AnalystAgent(llm_client=self.llm)

    async def run_pipeline(
        self,
        run_id: str,
        brief: ProductBrief,
        emit: Callable[[str, str, str, dict | None], Coroutine[Any, Any, None]],
    ) -> RunResult:
        logger.info(f"Starting pipeline execution for run_id='{run_id}'")

        # Save initial run record in SQLite
        async with get_db() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO runs (id, brief_json, status, result_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, brief.model_dump_json(), "running", None, time.time()),
            )
            await conn.commit()

        try:
            # Stage 1: AI Planner (Timeout 120s)
            try:
                plan: SearchPlan = await asyncio.wait_for(
                    self.planner.run(brief, emit), timeout=120.0
                )
            except TimeoutError:
                logger.warning("Planner stage timed out after 120s. Using fallback plan.")
                await emit(
                    "warning",
                    "planner",
                    "Planner LLM timed out. Using deterministic fallback plan.",
                    None,
                )
                plan = self.planner._build_deterministic_fallback(brief)

            # Stage 2: Concurrent Scraping (Timeout 300s)
            scrape_results = await asyncio.wait_for(
                asyncio.gather(
                    self.marketplace_scraper.run(plan, brief, emit),
                    self.social_scraper.run(plan, emit),
                    return_exceptions=True,
                ),
                timeout=300.0,
            )

            mk_scrapes: dict[PlatformName, PlatformScrape] = {}
            if isinstance(scrape_results[0], Exception):
                logger.error(f"Marketplace scraper failed: {scrape_results[0]}")
                await emit(
                    "warning",
                    "marketplace",
                    f"Marketplace scraping issue: {scrape_results[0]}",
                    None,
                )
            else:
                mk_scrapes = scrape_results[0]

            social_scrape: SocialScrape | None = None
            if isinstance(scrape_results[1], Exception):
                logger.error(f"Social scraper failed: {scrape_results[1]}")
                await emit(
                    "warning", "social", f"Social listening issue: {scrape_results[1]}", None
                )
            else:
                social_scrape = scrape_results[1]

            # Stage 3: Deterministic Scoring (Pure Python, 0 LLM calls)
            await emit(
                "stage", "analyst", "Running deterministic multi-factor keyword scoring...", None
            )
            scored_candidates = score_all(
                brief=brief, plan=plan, marketplace_scrapes=mk_scrapes, social=social_scrape
            )

            # Stage 4: AI Analyst (Timeout 150s)
            try:
                result: RunResult = await asyncio.wait_for(
                    self.analyst.run(
                        brief=brief,
                        plan=plan,
                        scored_candidates=scored_candidates,
                        marketplace_scrapes=mk_scrapes,
                        social_scrape=social_scrape,
                        emit=emit,
                    ),
                    timeout=150.0,
                )
            except TimeoutError:
                logger.warning("Analyst stage timed out. Using deterministic fallback.")
                await emit(
                    "warning",
                    "analyst",
                    "Analyst LLM timed out. Synthesized results using deterministic scoring engine.",
                    None,
                )
                result = self.analyst._synthesize_deterministic_fallback(
                    brief=brief,
                    scored_candidates=scored_candidates,
                    marketplace_scrapes=mk_scrapes,
                    note="Analyst timed out after 150s. Result compiled via deterministic scoring engine.",
                )
            result.run_id = run_id

            # Save completed result in SQLite
            async with get_db() as conn:
                await conn.execute(
                    """
                    UPDATE runs
                    SET status = ?, result_json = ?
                    WHERE id = ?
                    """,
                    ("completed", result.model_dump_json(), run_id),
                )
                await conn.commit()

            # Emit final SSE events
            await emit("result", "system", "Keywords and factors ready.", result.model_dump())
            await emit("done", "system", "Pipeline execution completed.", None)
            return result

        except Exception as err:
            logger.exception(f"Pipeline failed for run_id='{run_id}': {err}")
            async with get_db() as conn:
                await conn.execute("UPDATE runs SET status = ? WHERE id = ?", ("failed", run_id))
                await conn.commit()
            await emit("error", "system", f"Run failed: {err}", None)
            raise
