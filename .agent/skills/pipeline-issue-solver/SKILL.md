---
name: pipeline-issue-solver
description: Systematically analyzes runtime errors, terminal logs, and scraper bottlenecks; produces structured diagnostic reports; searches and designs robust solutions; and executes verified step-by-step implementations. Trigger when diagnosing terminal errors, LLM schema parsing failures, browser launch warnings, network blocks, or server crashes.
---

# Pipeline Issue Solver: Analysis, Reporting, Solution Search & Implementation

## When to Use This Skill
- Diagnosing runtime errors from terminal logs or server tracebacks.
- Analyzing LLM schema validation failures, prompt bloat, or 429 rate limit cascades.
- Addressing Playwright browser launch warnings or headless binary issues.
- Handling network blocks (e.g., HTTP 403, Cloudflare challenges).
- Resolving server startup, port binding, and process conflicts.

---

## The 4-Phase Resolution Framework

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ 1. ANALYZE       │ ──> │ 2. REPORT        │ ──> │ 3. SEARCH SOLUTION   │ ──> │ 4. IMPLEMENT & TEST │
│ Parse logs &     │     │ Structured issue │     │ Query codebase, KIs, │     │ Atomic code edits,   │
│ isolate root     │     │ taxonomy &       │     │ docs, and validated  │     │ regression pytests,  │
│ causes           │     │ impact matrix    │     │ design patterns      │     │ end-to-end check     │
└──────────────────┘     └──────────────────┘     └──────────────────────┘     └──────────────────────┘
```

---

## Phase 1: Analyze (Log Parsing & Root-Cause Isolation)

### 1.1 Checklist
- [ ] Capture the exact error signature from the active terminal buffer or log URI.
- [ ] Distinguish between fatal crashes, retryable warnings, and cosmetic stderr notices.
- [ ] Isolate which subsystem produced the error:
  - **Browser/Scraper**: Playwright binaries, channel detection, selectors, DOM changes.
  - **LLM/Client**: Prompt token length, JSON schema complexity, model availability, rate limits (429).
  - **Network/Security**: HTTP 403, 401, CORS, firewall, socket bind conflicts (`[WinError 10013]`).
  - **Data/Pydantic**: Type coercion (`float` vs `int`), missing attributes, validation errors.

### 1.2 Inspection Protocols
- **Inspect DB Runs**: Run `SELECT status, result_json FROM runs WHERE id='...'` to verify stage completion.
- **Inspect Server Logs**: Search for `WARNING` and `ERROR` tags with timestamp context.
- **Trace LLM Interactions**: Check prompt length (`prompt_len`), response status, and schema validation errors.

---

## Phase 2: Report (Structured Diagnostic Matrix)

Every diagnosis must produce a structured finding table using this standard schema:

| Issue ID | Subsystem | Severity | Error Signature | Root Cause | Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ERR-01` | Browser | Medium | `Executable doesn't exist at ms-playwright...` | Bundled Chromium shell missing; falls back to Edge | Noisy warning box in logs |
| `ERR-02` | LLM/Analyst | High | `Model output failed schema parsing (len=8801)` | Prompt bloat overwhelms free LLMs; complex JSON schema | Slow repairs, model fallback cascades, 429 risks |
| `ERR-03` | Social Scraper | Low | `Reddit returned 403 Blocked` | Unauthenticated `.json` requests rejected by Reddit | Missing Reddit social signals |

---

## Phase 3: Search for Solution (Pattern Matching & Design)

### 3.1 Solution Search Playbook
1. **Playwright Missing Executable**:
   - Check if `playwright install chromium` can be executed to install official binaries.
   - Or configure `BrowserManager` to launch system Edge directly without triggering the missing Chromium fallback warning.
2. **LLM Prompt Bloat & Schema Parsing**:
   - Calculate prompt tokens: Keep user prompt $\le 3,500$ characters for free-tier `:free` models.
   - Minify candidate pools: Send top 10 scored candidates instead of raw dumps.
   - Compact schema: Simplify nested dictionaries into flat key-value pairs or platform-specific targets.
   - Use smart JSON repair: Strip markdown fences (` ```json `), trailing commas, and extract outermost `{...}`.
   - Prioritize high-quality free models: Route to `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, or `nvidia/nemotron-3-super-120b-a12b:free` which excel at structured output.
3. **Network 403 Block Mitigation**:
   - Use cached fixture or alternative open fashion discussion feeds when Reddit restricts public access.
   - Never raise unhandled exceptions on 403; return polite `status="blocked"` with available signals.

---

## Phase 4: Implementation & Verification

### 4.1 Implementation Rules
- Apply changes atomically using `replace_file_content`.
- Never modify unrelated business logic or delete existing comments/docstrings.
- Ensure all types strictly match Pydantic v2 expectations.

### 4.2 Verification Gates
1. **Linter & Type Check**:
   - Run `tsc --noEmit` for frontend.
   - Run `ruff check backend/` or python syntax validation.
2. **Automated Test Suite**:
   - Run `pytest backend/tests` (must pass 100%).
   - Run `vitest run` for frontend components.
3. **Live End-to-End Pipeline Check**:
   - Execute test run (`test_pipeline.py`).
   - Confirm event stream finishes with `[system] done` and returns valid platform results.
