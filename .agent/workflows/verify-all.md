---
name: verify-all
description: Executes end-to-end verification of the Marketplace Keyword Agent system by checking backend startup, running automated linters and test suites, executing selector health checks, and compiling a structured pass/fail status table.
---

# Workflow: verify-all

Execute this workflow before opening pull requests, completing major features, or validating environment integrity.

## Prerequisites
- Python virtual environment activated with dependencies (`pip install -r backend/requirements.txt` or equivalent).
- Node.js dependencies installed (`cd frontend && npm install`).
- Headless Chromium installed (`playwright install chromium`).
- Valid backend `.env` configuration file present.

---

## Step-by-Step Execution Procedure

### Step 1: Start Backend Service and Health Probe
1. Launch the FastAPI development server in the background:
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```
2. Wait 3 seconds, then query the health endpoint:
   ```bash
   curl -s http://127.0.0.1:8000/api/health
   ```
3. Verify that the response returns `{"status": "ok"}` and confirms database connectivity.
4. Query the quota endpoint to verify OpenRouter free-tier quota status:
   ```bash
   curl -s http://127.0.0.1:8000/api/quota
   ```
   Confirm that the active model ends in `:free` and the API key is **not** exposed in the response payload.

### Step 2: Run Unified Automated Checks (`run_all_checks.sh`)
Execute the central quality verification script:
```bash
bash .agent/skills/testing-and-verification/scripts/run_all_checks.sh
```
This script validates:
- **Python Linting**: Ruff code formatting and lint rules across `backend/`.
- **Backend Tests**: Pytest test suite using `respx` mocked HTTP and `FakeLLM` fixtures.
- **TypeScript Static Typing**: `npx tsc --noEmit` on the frontend codebase.
- **Frontend Tests**: Vitest test suite on UI components (`BriefForm`, `PlatformResults`).
- **Production Build**: `vite build` compilation to ensure clean bundling.

### Step 3: Run Marketplace Selector Health Check
Verify that live marketplace selectors in `selectors.yaml` remain functional and detect any anti-bot or structural changes:
```bash
python .agent/skills/playwright-marketplace-scraper/scripts/selector_healthcheck.py
```
Review output for:
- Amazon.in search results and title/price selector matches.
- Myntra search cards and JSON state extraction.
- Flipkart structural selectors and login modal handling.

---

## Step 4: Compile and Report Pass/Fail Table

Compile the verification results and present the final status table to the user:

| Check Item | Scope / Command | Target Threshold | Result (Pass/Fail) | Notes |
|---|---|---|:---:|---|
| **Backend Startup & Health** | `GET /api/health` | HTTP 200 `{"status": "ok"}` | `[PASS / FAIL]` | Verified DB connectivity |
| **Quota Security Check** | `GET /api/quota` | `:free` model, NO leaked key | `[PASS / FAIL]` | Backend-only secret safety |
| **Python Linting (Ruff)** | `ruff check backend/` | Zero errors | `[PASS / FAIL]` | Code style & imports |
| **Backend Tests (Pytest)** | `pytest tests/ -v` | 100% tests passing | `[PASS / FAIL]` | Respx + FakeLLM mocks |
| **TypeScript Typecheck** | `tsc --noEmit` | Zero type errors | `[PASS / FAIL]` | Strict type definitions |
| **Frontend Tests (Vitest)** | `vitest run` | All component tests pass | `[PASS / FAIL]` | UI rendering & clean output |
| **Production Build** | `npm run build` | Successful Vite bundle | `[PASS / FAIL]` | Asset packaging |
| **Amazon Selector Health** | `selector_healthcheck.py` | Card & title selectors match | `[PASS / FAIL]` | Active or cached |
| **Myntra Selector Health** | `selector_healthcheck.py` | State/DOM selectors match | `[PASS / FAIL]` | Active or cached |
| **Flipkart Selector Health** | `selector_healthcheck.py` | Structural selectors match | `[PASS / FAIL]` | Active or cached |
| **Project Guardrails (DoD)** | Inspection against `project-guardrails.md` | All 9 guardrails satisfied | `[PASS / FAIL]` | <=4 agents, <=4 LLM calls |

*If any check fails, immediately review error logs, update selectors or unit tests, and re-run until all items show PASS.*
