---
description: Systematically audit, diagnose, and repair scraping adapters across B2C, B2B, quick commerce, and signal sources
---

# Workflow: Diagnose and Repair Sources

Run this workflow whenever scrapers fail, return 0 items, encounter selector drift, or fail automated canary checks.

## Phase 1: Run Diagnostics Tool

Execute the diagnostic canary runner against all enabled sources:

```bash
# Full diagnostic run across all sources
python .agent/skills/scraper-diagnostics-and-repair/scripts/diagnose_sources.py

# Or run for a specific failing source in headed mode for visual inspection
python .agent/skills/scraper-diagnostics-and-repair/scripts/diagnose_sources.py --only amazon --headed
```

This generates `source-health.md` in the workspace root and archives canary artifacts (screenshots, HTML snapshots, and captured network payloads) under `backend/data/debug/<source>/<timestamp>/`.

## Phase 2: Inspect `source-health.md`

Open `source-health.md` and review the failure categorization:
- **`blocked`**: CAPTCHA, Cloudflare turnstile, or robot shield.
  - *Action*: Stop immediately. Verify whether a public suggestion endpoint exists. If strictly bot-blocked, ensure status is recorded as `blocked` or toggle `default_enabled: false`. Never attempt stealth bypass.
- **`consent_or_location_modal`**: Pincode dialog, delivery city popup, or cookie banner obscuring search results.
  - *Action*: Add modal dismiss selectors or configure `DELIVERY_PINCODE` in adapter.
- **`login_wall`**: Authentication barrier preventing public browsing.
  - *Action*: Mark source `status_override: unavailable` with reason, or use unauthenticated public endpoints.
- **`selector_drift`**: DOM elements changed or class names hashed.
  - *Action*: Climb the strategy ladder. Switch to embedded JSON (`__NEXT_DATA__`, `window.__INITIAL_STATE__`) or network capture before rewriting CSS selectors.
- **`timing`**: Results rendered dynamically via client-side fetch after DOM loaded.
  - *Action*: Wait for explicit card selectors or network response events instead of relying on `networkidle`.
- **`resource_blocking`**: Missing critical scripts/styles due to overzealous blocking.
  - *Action*: Set `block_images: false` in `sources.yaml` if the target SPA breaks without asset loading.
- **`wrong_url`**: 404 or redirected URL template.
  - *Action*: Verify actual search URL in a real browser session.

## Phase 3: Implement Fix at Highest Ladder Rung

Refer to `.agent/skills/source-adapter-framework/SKILL.md` and fix the adapter following the 5-step strategy ladder:
1. Public autosuggest / search JSON endpoint
2. Embedded page JSON state (`<script type="application/json">` / `window.__state`)
3. Network interception (`page.on("response")`)
4. DOM selectors with ordered fallback chains
5. Structural text heuristics

## Phase 4: Record Sanitised Fixture & Update Tests

Update the offline regression fixture:

```bash
python .agent/skills/scraper-diagnostics-and-repair/scripts/record_fixture.py --source <source_id>
```

Run test suite to verify parser correctness:
```bash
pytest backend/tests/test_parsers.py -k <source_id>
```

## Phase 5: Re-run Canary Audit

Confirm the issue is resolved:

```bash
python .agent/skills/scraper-diagnostics-and-repair/scripts/diagnose_sources.py --only <source_id>
```

Ensure `source-health.md` reflects `PASS` or a verified `blocked`/`unavailable` state.
