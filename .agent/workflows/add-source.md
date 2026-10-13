---
description: Register and scaffold a new source adapter into the registry and workflow canvas
---

# Workflow: Add a New Source Adapter

Follow this workflow to integrate any new marketplace, B2B supplier, quick commerce, or social signal source.

## Phase 1: Scaffold Adapter & Registry Entry

Run the source scaffolding generator:

```bash
python .agent/skills/source-adapter-framework/scripts/new_source.py \
  --id <source_id> \
  --label "<Human Readable Label>" \
  --group "<marketplaces|b2b|quickcommerce|signals>" \
  --kind "<marketplace|b2b|quickcommerce|search|social>" \
  --hosts "target.domain.com"
```

This generates:
- Adapter file: `backend/app/scrapers/<source_id>.py` from `adapter_template.py`
- Test fixture directory: `backend/tests/fixtures/<source_id>/`
- Initial entry template in `backend/app/scrapers/sources.yaml`

## Phase 2: Live Verification in Browser

Open a clean browser session (or use Playwright headed mode):
1. Navigate to the platform's public search URL manually or via test script.
2. Check for public autosuggest endpoints in Network tab (e.g. `suggest?q=...` or `autocomplete?q=...`).
3. Check page source for embedded state (`__NEXT_DATA__`, `window.__INITIAL_STATE__`, JSON-LD).
4. Note whether search requires location/pincode selection or forces an unbypassable login wall.
5. If the site is an app-only walled garden or has no public search catalog, immediately set:
   ```yaml
   status_override: unavailable
   notes: "No public web search catalog available."
   ```

## Phase 3: Implement Strategy Ladder in Adapter

Open `backend/app/scrapers/<source_id>.py` and implement the 5-step ladder:
- **Strategy 1**: HTTP GET to public suggestion API (lightweight, zero browser overhead).
- **Strategy 2**: Embedded page JSON parser using BeautifulSoup / `re.search`.
- **Strategy 3**: Playwright network response listener for internal search API JSON.
- **Strategy 4**: Semantic DOM selectors with multiple fallbacks.
- **Strategy 5**: Structural heuristic fallback.

Ensure pure `parse(raw_content)` returns standard `Item` or `SocialSignal` objects.

## Phase 4: Record Sanitized Fixture & Unit Test

Capture offline fixture for regression testing:

```bash
python .agent/skills/scraper-diagnostics-and-repair/scripts/record_fixture.py --source <source_id>
```

Add parser unit test in `backend/tests/test_parsers.py`:
```python
def test_parse_<source_id>():
    with open("backend/tests/fixtures/<source_id>/canary.html", "r", encoding="utf-8") as f:
        content = f.read()
    items = parse_<source_id>(content)
    assert len(items) > 0
    assert items[0].title
```

## Phase 5: Outbound Allowlist & Security Verification

1. Ensure all source domains are declared under `hosts` in `sources.yaml`.
2. Confirm the host is added to `ALLOWLISTED_HOSTS` in `backend/app/net/safe_http.py`.
3. If `tos_risk: high`, confirm `SOURCES_ALLOW_HIGH_RISK=true` requirement is respected.
4. Run security and regression scans:
   ```bash
   python scripts/security_scan.py
   pytest backend/tests/
   ```

## Phase 6: Canvas Group & Visual Inspection

Start development servers and inspect the React Flow canvas:
1. Verify the new source node renders automatically inside its parent group node ("B2C marketplaces", "B2B and wholesale", "Quick commerce", or "Search and social").
2. Check that the node has the correct status badge, tool edge from parent agent, and metadata tooltip.
3. Test canvas collapse/expand functionality.
