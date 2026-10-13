# Project Guardrails: Marketplace Keyword Agent

This rule is **ALWAYS ON** for all agents and subagents working in this workspace.

---

## 1. Architectural Guardrails

1. **Strict 4-Agent Maximum**:
   - The entire system consists of strictly four agents:
     1. **AI Planner**
     2. **Marketplace Scraper**
     3. **Social Scraper**
     4. **AI Analyst**
   - **Adding a 5th agent is forbidden.** Extend tool functions or background tasks instead.

2. **OpenRouter Free Tier Only (`:free`)**:
   - Only model identifiers ending in `:free` are permitted (e.g. `google/gemini-2.0-flash-exp:free`, `meta-llama/llama-3.3-70b-instruct:free`).
   - Never hardcode a single model ID in application code; always use an ordered fallback chain loaded from environment variables.
   - Enforce an internal token-bucket rate limiter at $\le 16$ requests/minute to stay safely below the upstream ~20 RPM limit.

3. **Backend-Only API Key**:
   - The OpenRouter API key exists ONLY in the backend `.env` file and is loaded through `pydantic-settings` as a `SecretStr`.
   - The key must **never** reach the frontend browser, git repositories, client-side bundles, or API responses (`/api/health`, `/api/quota`, error traces).

4. **Minimise LLM Calls ($\le 4$ per Run)**:
   - Target total LLM consumption is $\le 3\text{--}4$ calls per seller run:
     - Planner: 1 call.
     - Marketplace Scraper: 0 calls (pure deterministic tools).
     - Social Scraper: 0 or 1 call (optional clustering).
     - Scoring: 0 calls (pure Python mathematical formula).
     - Analyst: 1 call (synthesis).
   - Batch operations instead of making repeated conversational calls.

---

## 2. Scraping & Politeness Guardrails

5. **Never Bypass Logins or CAPTCHAs**:
   - Never attempt to solve or automate around CAPTCHAs or Cloudflare/bot challenge screens.
   - On encountering a CAPTCHA or bot check, immediately abort the scrape for that platform and return `status="blocked"`.
   - Never store or solicit user credentials for X, Instagram, Amazon, Myntra, or Flipkart.
   - X and Instagram adapters must remain disabled by default behind `ENABLE_X` and `ENABLE_INSTAGRAM` environment flags.

6. **Cache First (24-Hour TTL)**:
   - Always query the local SQLite cache (`scrape:{platform}:{query}` and `social:{source}:{query}`) before executing any external web request.
   - Prefer lightweight public autosuggest JSON endpoints over heavy headless browser navigations whenever possible.

---

## 3. UI/UX Guardrails

7. **Keywords-Only in Platform Output Sections**:
   - Platform results cards must display **strictly plain keyword chips** and a "Copy All" button.
   - **Zero clutter**: No search volume bars, no confidence numbers, no score metrics, no charts, and no promotional copy inside platform cards.
   - Strategic analysis, pricing context, GSM details, and trademark flags belong exclusively in the separate **"Other factors"** section.

---

## 4. Engineering & Quality Guardrails

8. **All New Code Requires Tests**:
   - Every service, scraper parser, and component must have unit test coverage.
   - All tests must use mocked responses (`respx`, `FakeLLM`, local HTML fixtures) to avoid consuming live LLM quota or spamming retail sites.
   - Rate limiters must be tested with fake clocks, never real sleeps.

9. **Update Documentation Continuously**:
   - Whenever system behavior, schemas, or environment variables change, update `README.md` and related skill playbooks immediately.

---

## 5. Security & Professional Design Guardrails

10. **Design & Code Hardening Standards**:
    - UI must follow `professional-ui-design-system`; no emoji icons, no gradient/glow styling.
    - No `dangerouslySetInnerHTML`.
    - All untrusted text is rendered as plain text and gated before use.
    - Outbound requests only to the host allowlist.
    - Run `scripts/security_scan.sh` before declaring a task done.

---

## 6. Source Adapter & Scraper Guardrails

11. **Registry-Driven Source Adapters**:
    - **New sources are adapters, never new agents.** The system strictly retains its 4 core agents (Planner, Marketplace Scraper, Social Scraper, Analyst).
    - **Every adapter is registered in `sources.yaml`.** Hardcoding platform endpoints or scrapers outside the registry is prohibited.
    - **Always verify selectors and endpoints live before trusting hints.** Never rely on outdated static selector lists.
    - **Prefer embedded JSON and network capture over brittle DOM selectors.** Ascend the strategy ladder before falling back to DOM scraping.
    - **Never bypass blocks.** Never use stealth/evasion plugins, proxy rotation, CAPTCHA solvers, or anti-bot workarounds.
    - **Never use Google's Custom Search JSON API.** (Closed to new customers and retires on 1 January 2027).
    - **Record a fixture and a parser test for every adapter.** Every source must be backed by a sanitised HTML/JSON fixture and deterministic unit tests.
