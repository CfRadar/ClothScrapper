---
name: scraper-diagnostics-and-repair
description: Provides systematic diagnostic workflows, failure taxonomy classification, and repair protocols for failing scraping adapters. Trigger when scrapers return 0 items, encounter selector drift, trigger bot blocks, or break due to DOM changes.
---

# Scraper Diagnostics and Repair

## Purpose
Establishes a rigorous, systematic procedure to diagnose why a marketplace or signal source fails, classify the root cause according to an actionable failure taxonomy, and resolve the failure at the highest possible rung of the strategy ladder without anti-detection hacks.

---

## When to Use
- A source adapter returns 0 items or raises navigation timeouts.
- Platform HTML markup has changed or class names have been randomized (selector drift).
- Inspecting canary test failures or writing new parser fixtures.
- Investigating `blocked` or `degraded` statuses reported on the workflow canvas.

---

## The Failure Taxonomy

When diagnosing failures, classify the cause into one of the following canonical buckets:

| Failure Cause | Symptoms & Detection | Actionable Fix |
|---|---|---|
| **`blocked`** | HTTP 403, 429, Cloudflare Turnstile, CAPTCHA image, "Robot Check". | **Stop immediately.** Never bypass or automate around challenges. Switch to public autosuggest JSON endpoint or mark `status="blocked"`. |
| **`consent_or_location_modal`** | Fullscreen backdrop asking for delivery pincode, city, or cookie consent. | Identify modal dismiss selector, or automate entering `DELIVERY_PINCODE` (e.g. `110001`) during setup. |
| **`login_wall`** | Forced redirect to `/login` or popup "Sign in to see search results". | Verify if unauthenticated public URL exists. If walled garden, set `status_override: unavailable`. |
| **`lazy_load`** | Only 2–4 items parsed; remaining items populate only after scroll. | Implement step-scrolling (`window.scrollBy(0, 800)`) with a stabilization pause until card count stabilizes. |
| **`timing`** | Parser runs before client-side SPA hydration renders cards. | Never rely on `networkidle`. Use `page.wait_for_selector(card_sel, timeout=10000)` or wait for XHR response. |
| **`selector_drift`** | Status 200, full HTML payload, but CSS selectors match 0 elements. | Move up the strategy ladder: extract embedded JSON (`__NEXT_DATA__`, `window.__INITIAL_STATE__`) or network response JSON. |
| **`wrong_url`** | HTTP 404, redirect loop, or empty search parameters. | Verify real search URL live in browser; update `url_templates.search` in `sources.yaml`. |
| **`resource_blocking`** | SPA breaks or renders blank white page when images/fonts blocked. | Toggle `block_images: false` in `sources.yaml` for that specific source adapter. |
| **`geo_or_locale`** | Non-Indian currency (USD instead of INR) or missing regional items. | Set Playwright browser context with `locale="en-IN"`, `timezone_id="Asia/Kolkata"`. |
| **`rate_limited`** | HTTP 429 after rapid sequential requests. | Increase `delay_min` and `delay_max` jitter parameters in `sources.yaml`. |

---

## Browser Guidance & Security Constraints

- **Allowed Browser**: Playwright Chromium (or system Google Chrome / Microsoft Edge via `channel="chrome"` / `channel="msedge"`).
- **Navigation Lifecycle**: Use `wait_until="domcontentloaded"` combined with explicit selector waits. Avoid `networkidle` which often hangs indefinitely on analytics pings.
- **Realistic Context**: Configure standard user agent, `en-IN` locale, and 1440x900 desktop viewport.
- **FORBIDDEN Anti-Patterns**:
  - **NO** stealth / evasion plugins (`playwright-stealth`, puppeteer-stealth, selenium-stealth).
  - **NO** proxy rotation services or residential proxy pools.
  - **NO** automated CAPTCHA solvers (2Captcha, AntiCaptcha, AI solvers).
  - **NO** account credential harvesting or simulated user logins.

---

## Step-by-Step Diagnostic Procedure

### 1. Run Automated Diagnostics
Execute the diagnostic canary tool for the failing source:

```bash
python .agent/skills/scraper-diagnostics-and-repair/scripts/diagnose_sources.py --only amazon --headed
```

Review artifacts saved under `backend/data/debug/<source>/<timestamp>/`:
- `screenshot.png`: Visual layout, reveals modals or bot checks.
- `page.html`: Raw server response.
- `network.json`: Captured API endpoints and JSON responses.

### 2. Ascend the Strategy Ladder
Once the cause is classified, repair the adapter using the highest viable strategy:
1. **Did network capture find an internal JSON API?** -> Switch adapter to intercept that endpoint.
2. **Does HTML contain `<script id="__NEXT_DATA__">`?** -> Parse JSON directly via `json.loads`.
3. **If forced to use DOM**: Write semantic selectors (e.g. `div[data-component-type='s-search-result']`) with at least 2 fallback alternatives.

### 3. Record Sanitized Fixture
Capture the newly working response to keep unit tests synchronized:

```bash
python .agent/skills/scraper-diagnostics-and-repair/scripts/record_fixture.py --source amazon
```

Verify fixture age is `< 90 days`.

### 4. Verify Offline Parser Tests
Ensure parser tests in `backend/tests/test_parsers.py` pass without network access:

```bash
pytest backend/tests/test_parsers.py -k amazon -v
```

---

## Checklist Before Finishing
- [ ] Diagnostic canary artifacts reviewed in `backend/data/debug/`.
- [ ] Root cause classified accurately against the Failure Taxonomy.
- [ ] Adapter updated to the highest feasible ladder rung (preferring JSON over DOM).
- [ ] Zero stealth hacks or evasion plugins introduced.
- [ ] Offline test fixture refreshed and parser unit test passes.
