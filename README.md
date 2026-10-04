# Marketplace Keyword Agent

A specialized multi-agent e-commerce intelligence system designed for Indian fashion marketplace sellers. A seller fills in a T-shirt product brief, and the application returns high-intent search keywords for **Amazon.in**, **Myntra**, and **Flipkart**, presented strictly as clean keyword chips per platform, accompanied by a structured "Other factors" section and an interactive AI customization chat block.

---

## Architecture Overview

The system strictly coordinates **exactly 4 agents** using plain `asyncio` workflows (no LangChain / LangGraph), streaming real-time status updates to the client via Server-Sent Events (SSE):

```text
                       +---------------------------+
                       |   Seller Product Brief    |
                       +-------------+-------------+
                                     |
                                     v
                       +---------------------------+
                       | Agent 1: AI Planner (LLM) |
                       | - Target market inference |
                       | - Platform search queries |
                       | - Social listening seeds  |
                       +-------------+-------------+
                                     |
                 +-------------------+-------------------+
                 |                                       |
                 v                                       v
   +---------------------------+           +---------------------------+
   |  Agent 2: Marketplace     |           |  Agent 3: Social Scraper  |
   |           Scraper (0 LLM) |           |           (<= 1 LLM)      |
   | - Amazon.in live & suggest|           | - Reddit public JSON API  |
   | - Myntra HTML & suggest   |           | - X / IG (best effort)    |
   | - Flipkart DOM & related  |           | - LLM normalization       |
   +-------------+-------------+           +-------------+-------------+
                 |                                       |
                 +-------------------+-------------------+
                                     |
                                     v
                       +---------------------------+
                       | Deterministic Scoring     |
                       | Engine (Pure Python)      |
                       | - N-gram extraction (1-4) |
                       | - Mathematical rank/score |
                       | - Brand & conflict drops  |
                       +-------------+-------------+
                                     |
                                     v
                       +---------------------------+
                       | Agent 4: AI Analyst (LLM) |
                       | - Platform keyword rank   |
                       | - Strategic other factors |
                       | - Interactive Chat block  |
                       +-------------+-------------+
                                     |
                                     v
                       +---------------------------+
                       | React 18 Clean UI         |
                       | - Keywords chips ONLY     |
                       | - Other factors accordion |
                       | - Real-time progress bar  |
                       | - AI customization chat   |
                       +---------------------------+
```

---

## Hard Constraints & Budget

| Constraint | Implementation Detail |
|---|---|
| **Agent Count** | **Strictly 4 agents**: Planner, Marketplace Scraper, Social Scraper, Analyst (Analyst also powers chat). No 5th agent. |
| **LLM Provider** | **OpenRouter Free Tier only** (model IDs ending with `:free`). Token bucket rate-limited to <= 16 req/min. |
| **Call Budget** | **Target <= 4 LLM calls per run** (Planner: 1, Social: 0-1, Analyst: 1) and 1 call per chat message. |
| **API Key Privacy** | Loaded only in `backend/app/config.py` from `backend/.env`. Never exposed in API responses, logs, SSE, or frontend code. |
| **UI Presentation** | Platform keyword cards render **only keyword chips** and a "Copy all" button. No metrics, scores, or charts. |
| **Polite Scrapers** | 24-hour SQLite caching, sequential requests per domain (concurrency=1), random 2-5s delays, graceful degradation to `blocked` on CAPTCHA. |

### LLM Call Budget Table

| Step | Normal Calls | Fallback Calls | Description |
|---|---|---|---|
| **Agent 1: Planner** | 1 | 0 (Deterministic) | Analyzes brief, infers target market, generates queries. |
| **Agent 3: Social Scraper** | 1 | 0 (Top count) | Normalizes raw community phrases into search keywords. |
| **Agent 4: Analyst (Run)** | 1 | 0-3 (Per-platform) | Synthesizes top candidates & computes marketplace factors. |
| **Chat Interaction** | 1 | 0 | Customizes keywords or answers seller questions. |
| **Typical Run Total** | **3 calls** | **<= 4 calls** | Bounded well within free-tier caps (~45 calls/day = 12-14 runs/day). |

---

## Prerequisites

- **Python**: 3.11+ (Python 3.12, 3.13, 3.14 supported)
- **Node.js**: 20+ (Node v20.x, v22.x, v24.x)
- **Chromium for Playwright**: `playwright install chromium`
- **OpenRouter Account**: Free API key from [openrouter.ai/keys](https://openrouter.ai/keys)

---

## Quickstart (Under 5 Minutes)

### 1. Clone & Setup Backend

```bash
# Clone the repository
cd marketplace-keyword-agent

# Install backend dependencies & setup environment
make setup
```

Or manually:
```bash
# Backend setup
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment & Discover Free Models

Copy the environment template:
```bash
cp backend/.env.example backend/.env
```

Discover currently active free OpenRouter models:
```bash
python backend/scripts/discover_free_models.py
```
Open `backend/.env` and paste your `OPENROUTER_API_KEY`, setting the discovered free models:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxx
MODEL_PLANNER=thinkingmachines/inkling-small:free
MODEL_ANALYST=thinkingmachines/inkling:free
MODEL_SOCIAL=nvidia/nemotron-3.5-lightning:free
MODEL_FALLBACKS=nvidia/nemotron-3-ultra-550b-a55b:free,dots-studio/dots-3-note-preview:free
```

### 3. Setup Frontend

```bash
cd frontend
npm install
```

### 4. Run the Application

In terminal 1 (Backend):
```bash
# From workspace root
make backend
# or: cd backend && python -m uvicorn app.main:app --reload --port 8000
```

In terminal 2 (Frontend):
```bash
# From workspace root
make frontend
# or: cd frontend && npm run dev
```

Open your browser at **`http://localhost:5173`**.

---

## Verification & Testing

Run all automated checks across backend and frontend with a single command:
```bash
make check
```

Or run individual verification steps:
```bash
# Backend code quality and style
python -m ruff check backend/

# Backend automated test suite (29 tests)
python -m pytest backend/tests/ -v

# Frontend TypeScript compiler check
cd frontend && npx tsc --noEmit

# Frontend unit and component tests
cd frontend && npm test -- --run

# Frontend production build
cd frontend && npm run build
```

### Selector Healthcheck

Verify marketplace CSS selectors against live DOM changes without running full scrapes:
```bash
python backend/scripts/selector_healthcheck.py
```

---

## Inspecting Database & Cache

To inspect cached marketplace scrapes, daily LLM quotas, and past runs:
```bash
python backend/scripts/inspect_db.py
```

---

## Selector Maintenance Guide

Marketplaces regularly update their markup and obfuscate class names. Selectors are isolated in [`backend/app/scrapers/selectors.yaml`](backend/app/scrapers/selectors.yaml) with an ordered fallback strategy:

1. **Amazon.in**: Uses `div[data-component-type="s-search-result"]`. If titles or prices shift, update the corresponding fallback list in `selectors.yaml`.
2. **Myntra**: Parses embedded `window.__myntraState` script JSON first. If the state payload changes, falls back to DOM selectors `li.product-base`, `h3.product-brand`, and `h4.product-product`.
3. **Flipkart**: Uses structural anchor patterns `a[href*="/p/"][href*="pid="]` and card regex parsers for prices (`₹[\d,]+`) to stay resilient to daily class hashing.

To update selectors:
1. Open the marketplace search URL in browser DevTools.
2. Identify stable attributes (e.g. `data-*`, semantic tags, or URL regexes).
3. Append or reorder the selector in `backend/app/scrapers/selectors.yaml`.
4. Run `python backend/scripts/selector_healthcheck.py` to verify match counts.

---

## Troubleshooting

### 1. HTTP 429 Rate Limits
- The backend features an integrated token bucket rate limiter (`LLM_RPM_LIMIT=16`) and exponential backoff (2s, 4s, 8s with jitter) before switching to the next `:free` fallback model.
- If you hit OpenRouter's global daily cap, the UI surfaces a clear quota indicator and gracefully falls back to deterministic pure-Python keyword ranking.

### 2. Marketplace Blocked / CAPTCHA
- If Amazon, Myntra, or Flipkart presents a CAPTCHA or robot wall, the platform scraper marks its status as `blocked` and stops further requests to that domain.
- **The run never fails**: The pipeline continues with remaining platforms, and the scoring engine synthesizes cross-platform and taxonomy candidates for the blocked marketplace with an amber UI warning.

### 3. Empty Social Results
- Reddit queries use public search JSON (`https://www.reddit.com/search.json`). If Reddit is temporarily unreachable or ratelimited, the Social Scraper returns empty signals without failing the pipeline.
- X and Instagram adapters are disabled by default (`ENABLE_X=false`, `ENABLE_INSTAGRAM=false`) and run in strictly best-effort unauthenticated mode.

---

## Legal & Compliance Disclaimer

> [!WARNING]
> Web scraping e-commerce marketplaces may be subject to platform Terms of Service, rate limits, and intellectual property guidelines. This software is provided for educational and research purposes. Users are solely responsible for ensuring compliance with applicable platform terms, data privacy regulations, and local laws.
