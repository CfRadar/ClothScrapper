---
name: multi-agent-orchestration
description: Coordinates the 4-agent pipeline using plain asyncio workflows, Pydantic RunState models, and SSE event streaming. Use when orchestrating the Planner, Marketplace Scraper, Social Scraper, and Analyst agents, managing stage timeouts, or enforcing the strict 4-agent maximum constraint.
---

# Multi-Agent Orchestration

## Purpose
This skill governs the execution lifecycle of the **Marketplace Keyword Agent** system. It uses clean, lightweight Python `asyncio` orchestration (without heavy, bloated multi-agent frameworks) to manage exactly 4 specialized agents. It coordinates state transitions, per-stage timeouts, fault-tolerant concurrent scraping, SSE streaming events, and enforces a strict budget of **<= 3-4 LLM calls per run**.

## When to use
- When designing or modifying the backend pipeline orchestrator (`WorkflowOrchestrator`).
- When defining the shared `RunState` Pydantic models.
- When sequencing tasks between the Planner, Scrapers, and Analyst.
- When handling partial scraper failures (e.g. Amazon succeeds but Myntra returns CAPTCHA).
- When streaming real-time stage progress over Server-Sent Events (SSE).

## Agent Architecture: Exactly 4 Agents

The system is strictly capped at **four agents**. Adding a 5th agent is forbidden; all auxiliary tasks must be implemented as tools.

1. **Agent 1: AI Planner**
   - *Role*: Analyzes seller brief, extracts normalized attributes, identifies target shopper persona, and formulates tailored search queries for Amazon.in, Myntra, and Flipkart.
   - *LLM Calls*: Exactly **1 call**.
2. **Agent 2: Marketplace Scraper Agent**
   - *Role*: Tool-driven execution agent. Runs Playwright scraping on Amazon.in, Myntra, and Flipkart with fallback selectors and autosuggest queries.
   - *LLM Calls*: Exactly **0 calls** (pure deterministic web tools).
3. **Agent 3: Social Scraper Agent**
   - *Role*: Queries Reddit fashion subreddits for community discussion, wishlist phrases, and fashion hashtags.
   - *LLM Calls*: **0 or 1 call** (only if needed to cluster complex colloquial phrases).
4. **Agent 4: AI Analyst Agent**
   - *Role*: Ingests the top 60 scored candidates from the Python scoring engine. Formats platform-specific keyword lists, generates the "Other factors" analysis section, and handles interactive seller follow-up questions in the chat block.
   - *LLM Calls*: Exactly **1 call** for synthesis (+ 1 per user chat message).

### LLM Call Budget Table

| Stage | Responsible Agent | Max LLM Calls | Provider / Model | Failure Action |
|---|---|:---:|---|---|
| 1. Query Planning | **AI Planner** | 1 | OpenRouter `:free` | Fallback to regex attribute query template |
| 2. E-Commerce Scrape | **Marketplace Scraper** | 0 | None (Tool-driven) | Tolerate partial failures; use cached data |
| 3. Social Listening | **Social Scraper** | 0 - 1 | OpenRouter `:free` | Fallback to raw regex wish/ask phrases |
| 4. Scoring Engine | *Python Tool (Deterministic)* | 0 | None (Pure Python) | N/A (Always succeeds) |
| 5. Keyword Synthesis | **AI Analyst** | 1 | OpenRouter `:free` | Output raw top 30 scored terms directly |
| **Total Pipeline Run** | **All 4 Agents** | **<= 3 - 4** | **OpenRouter :free** | **Never exceed 4 calls per run** |

## Step-by-step procedure

1. **Initialize Shared RunState**:
   - Create a central Pydantic model for the run:
     ```python
     class RunState(BaseModel):
         run_id: str
         brief: SellerBrief
         status: Literal["init", "planning", "scraping", "scoring", "analyzing", "completed", "failed"]
         queries: dict[str, list[str]] = {}
         marketplace_data: dict[str, PlatformScrapeResult] = {}
         social_signals: list[SocialSignal] = []
         scored_candidates: dict[str, list[ScoredKeyword]] = {}
         final_result: FinalAnalysisResult | None = None
         errors: list[str] = []
     ```

2. **Stage 1: AI Planner Execution**:
   - Input: Raw seller brief string + selected platforms.
   - Call Planner LLM (1 call) with strict JSON output.
   - Output: Normalized attributes and 2-3 search queries per selected platform.
   - Timeout: 30 seconds.

3. **Stage 2: Parallel Scraping (`asyncio.gather`)**:
   - Launch Marketplace Scraper and Social Scraper concurrently:
     ```python
     async def run_parallel_scrapers(state: RunState, emitter: EventEmitter):
         await emitter.emit("stage_start", stage="scraping", message="Gathering marketplace and social signals...")
         
         marketplace_task = asyncio.create_task(
             marketplace_scraper.scrape_all(state.queries),
             name="marketplace_task"
         )
         social_task = asyncio.create_task(
             social_scraper.listen(state.brief.attributes),
             name="social_task"
         )
         
         results = await asyncio.gather(marketplace_task, social_task, return_exceptions=True)
         # Gracefully handle exceptions without failing entire run
     ```
   - Partial tolerance: If Myntra fails or blocks, Amazon and Flipkart data must still proceed.

4. **Stage 3: Deterministic Keyword Scoring**:
   - Zero LLM calls. Execute `score_platform_candidates()` across scraped outputs.
   - Attach top ~60 candidate keywords per platform to `RunState.scored_candidates`.

5. **Stage 4: AI Analyst Synthesis**:
   - Input: Brief + Top 60 scored candidates per platform + social trends.
   - Call Analyst LLM (1 call) to prune trademarks, organize final keywords, and compose the "Other factors" section.
   - Output: Clean keywords per platform + other factors markdown.

6. **Stage 5: Interactive Chat Block**:
   - User can ask follow-up questions (e.g. "Suggest 5 more keywords for college students").
   - Analyst Agent answers with single targeted LLM call, referencing `RunState` context.

## Rules (do / don't)
- **DO** use plain standard library `asyncio` for task coordination.
- **DO** tolerate partial scraper failures; never cancel the whole run if one platform is blocked.
- **DO** emit real-time SSE progress events at every stage transition.
- **DO** enforce per-stage timeouts (Planner: 30s, Scraping: 90s, Analyst: 45s).
- **DON'T** add a 5th agent under any circumstances. Extend tools instead.
- **DON'T** use heavy orchestration frameworks like LangChain, CrewAI, or AutoGen.
- **DON'T** allow the total pipeline to exceed 4 LLM calls.

## Examples

### Stage Graph Execution Pattern
```python
async def execute_run_pipeline(brief: SellerBrief, emitter: EventEmitter) -> RunState:
    state = RunState(run_id=uuid4().hex, brief=brief, status="init")
    
    # 1. Planner (1 LLM call)
    await emitter.emit("stage", stage="planner", message="Generating search plan...")
    state.queries = await planner_agent.plan(state.brief)
    
    # 2. Scrapers in Parallel (0-1 LLM calls total)
    await emitter.emit("stage", stage="scraper", message="Scraping live data...")
    m_data, s_data = await asyncio.gather(
        marketplace_agent.run(state.queries),
        social_agent.run(state.brief),
        return_exceptions=True
    )
    state.marketplace_data = m_data if not isinstance(m_data, Exception) else {}
    state.social_signals = s_data if not isinstance(s_data, Exception) else []
    
    # 3. Deterministic Scoring (0 LLM calls)
    await emitter.emit("stage", stage="scoring", message="Calculating keyword scores...")
    state.scored_candidates = run_deterministic_scoring(state)
    
    # 4. Analyst (1 LLM call)
    await emitter.emit("stage", stage="analyst", message="Curating platform keywords...")
    state.final_result = await analyst_agent.synthesize(state)
    
    state.status = "completed"
    await emitter.emit("complete", stage="done", data=state.final_result.dict())
    return state
```

## Checklist before finishing
- [ ] Exactly 4 agents defined: Planner, Marketplace Scraper, Social Scraper, Analyst.
- [ ] LLM budget explicitly tracked and verified to stay $\le 4$ calls per run.
- [ ] Orchestration uses native Python `asyncio` and `RunState` Pydantic model.
- [ ] Scraper execution runs concurrently via `asyncio.gather(..., return_exceptions=True)`.
- [ ] Stage timeouts and partial-result resilience implemented.
- [ ] Zero 5th agents added.
