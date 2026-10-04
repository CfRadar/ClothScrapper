---
name: testing-and-verification
description: Specifies automated testing standards across backend and frontend, including respx HTTP mocking, FakeLLM fixtures, recorded HTML parser fixtures, Vitest component testing, and run_all_checks.sh. Use when creating tests, validating pull requests, or verifying project guardrails.
---

# Testing and Verification

## Purpose
This skill defines the testing harness and quality verification workflow for the **Marketplace Keyword Agent**. To protect the scarce OpenRouter free-tier quota and avoid spamming external retail sites during CI/CD, all automated tests rely on deterministic mocks: `respx` for HTTP mocking, a `FakeLLM` returning static JSON fixtures, recorded local HTML files for marketplace parsers, a fake clock for rate limiters, and Vitest for frontend components.

## When to use
- When writing unit tests for backend services, scrapers, rate limiters, or scoring logic.
- When writing frontend component tests for `BriefForm`, `PlatformResults`, or the SSE stream.
- When verifying that code complies with project guardrails before committing.
- When running the full suite via `scripts/run_all_checks.sh`.

## Step-by-step procedure

1. **Backend Testing Stack Setup**:
   - Install test dependencies:
     `pip install pytest pytest-asyncio respx ruff`
   - Configure `pytest.ini` with `asyncio_mode = auto`.

2. **Implement FakeLLM & Fixture Injection**:
   - Never call OpenRouter in automated unit tests.
   - Implement `FakeLLM` class that returns predefined JSON fixtures:
     ```python
     class FakeLLM:
         def __init__(self, fixture_data: dict):
             self.fixture_data = fixture_data
             self.call_count = 0

         async def complete(self, prompt: str) -> str:
             self.call_count += 1
             return json.dumps(self.fixture_data)
     ```

3. **Mock External HTTP Calls with `respx`**:
   - Mock Reddit search and autosuggest endpoints using `respx`:
     ```python
     import respx
     import httpx

     @respx.mock
     async def test_reddit_scraper():
         respx.get("https://www.reddit.com/r/IndianStreetwear/search.json").respond(
             status_code=200,
             json={"data": {"children": [{"data": {"title": "Looking for heavy 240 GSM oversized tees"}}]}}
         )
         signals = await scrape_reddit("oversized")
         assert len(signals) == 1
         assert "240 GSM" in signals[0]["title"]
     ```

4. **Marketplace Parser Tests with Recorded HTML Fixtures**:
   - Save sample HTML dumps in `tests/fixtures/`:
     - `amazon_search_results.html`
     - `myntra_search_results.html`
     - `flipkart_search_results.html`
   - Feed local HTML directly into parser functions:
     ```python
     def test_amazon_parser_with_html_fixture():
         with open("tests/fixtures/amazon_search_results.html", "r", encoding="utf-8") as f:
             html = f.read()
         products = parse_amazon_html(html)
         assert len(products) > 0
         assert products[0].title != ""
     ```

5. **Rate-Limiter Tests with Fake Clock**:
   - Validate token-bucket behavior without executing real `time.sleep()` delays:
     ```python
     def test_rate_limiter_blocks_above_capacity(monkeypatch):
         current_time = 1000.0
         def mock_time():
             return current_time
         # Advance mock_time manually to test token refill
     ```

6. **Frontend Testing with Vitest & React Testing Library**:
   - Test `BriefForm`: Verify platform selection checkboxes and validation on empty input.
   - Test `PlatformResults`: Verify that keyword chips render without scores or volume numbers, and clicking "Copy All" triggers clipboard API.
   - Run via `npx vitest run`.

7. **Execute Complete Verification Script**:
   - Run `bash scripts/run_all_checks.sh`:
     1. `ruff check backend/`
     2. `pytest tests/ -v`
     3. `npx tsc --noEmit`
     4. `npx vitest run`
     5. `npm run build`

## Definition of Done (DoD) Checklist

Before any code modification or pull request is deemed complete, verify:
- [ ] **Guardrail 1: Max 4 Agents**: System contains strictly Planner, Marketplace Scraper, Social Scraper, Analyst.
- [ ] **Guardrail 2: OpenRouter Free Models**: Only model IDs ending in `:free` are referenced.
- [ ] **Guardrail 3: Zero Secret Leakage**: API key never appears in frontend, git commits, or API responses.
- [ ] **Guardrail 4: Clean Keyword UI**: Platform keyword cards contain only plain keyword chips and "Copy All" (no charts, no scores).
- [ ] **Guardrail 5: LLM Call Budget**: Pipeline executes within $\le 4$ calls per run.
- [ ] **Guardrail 6: No CAPTCHA/Login Bypass**: Scrapers fail gracefully with `status="blocked"`.
- [ ] **Guardrail 7: Caching**: 24h SQLite cache checked before scraping.
- [ ] **Guardrail 8: Test Coverage**: All new services and components have accompanying automated tests.
- [ ] **Guardrail 9: Clean Checks**: `scripts/run_all_checks.sh` exits with code 0.

## Rules (do / don't)
- **DO** use `respx` to mock all external HTTP endpoints during automated testing.
- **DO** use local recorded HTML fixtures to test marketplace parsing resilience.
- **DO** ensure `scripts/run_all_checks.sh` passes completely before marking a task done.
- **DON'T** make live calls to OpenRouter or external marketplaces in automated unit test runs.
- **DON'T** use real `time.sleep()` in rate limiter unit tests; use fake clocks or monkeypatched time.
- **DON'T** commit secrets or real API keys in test fixtures or mock configurations.

## Examples

### FakeLLM Integration Test Example
```python
import pytest
from backend.services.orchestrator import WorkflowOrchestrator
from backend.models.schemas import SellerBrief

@pytest.mark.asyncio
async def test_full_pipeline_with_mocks():
    fake_planner_response = {
        "attributes": {"fit": "oversized", "fabric": "cotton"},
        "queries": {"amazon": ["oversized cotton t shirt"]}
    }
    fake_llm = FakeLLM(fake_planner_response)
    orchestrator = WorkflowOrchestrator(llm_client=fake_llm)
    
    brief = SellerBrief(description="Black oversized cotton tee", platforms=["amazon"])
    run_state = await orchestrator.run(brief)
    
    assert run_state.status == "completed"
    assert "amazon" in run_state.queries
    # Total LLM calls during automated test should be strictly bounded
    assert fake_llm.call_count <= 2
```

## Checklist before finishing
- [ ] `pytest`, `pytest-asyncio`, and `respx` installed and configured.
- [ ] `FakeLLM` fixture class implemented for mock completions.
- [ ] Local HTML fixtures present for Amazon, Myntra, and Flipkart parser tests.
- [ ] Vitest component tests implemented for form and keyword display.
- [ ] `scripts/run_all_checks.sh` executable and passing.
- [ ] Project guardrails validated against DoD checklist.
