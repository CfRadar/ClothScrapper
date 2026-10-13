---
name: source-adapter-framework
description: Governs the registry-driven SourceAdapter architecture, the 5-step strategy ladder, circuit breakers, and sources.yaml configuration for scaling the application to 40+ sources. Trigger when implementing or registering any new marketplace, B2B, quick commerce, or signal source.
---

# Source Adapter Framework

## Purpose
Establishes a unified, registry-driven plugin system for external data sources. Sources are modular adapters—never new agents. Every source conforms to a standardized Python protocol, is declared in `backend/app/scrapers/sources.yaml`, ascends a polite 5-step strategy ladder, and automatically renders onto the React Flow canvas.

---

## When to Use
- Adding any new retail marketplace (e.g. Ajio, Snapmint), B2B platform (e.g. IndiaMART, Alibaba), quick commerce app (e.g. Blinkit, Zepto), or signal provider (e.g. Google, Pinterest).
- Refactoring existing scrapers (Amazon.in, Myntra, Flipkart) into standard protocol adapters.
- Configuring fallback strategies, circuit breakers, or outbound host allowlists.

---

## Step-by-Step Procedure

### 1. Scaffold the Adapter
Use the built-in generator to create the adapter file, test fixture directory, and YAML entry:

```bash
python .agent/skills/source-adapter-framework/scripts/new_source.py \
  --id ajio \
  --label "Ajio" \
  --group "marketplaces" \
  --kind "marketplace" \
  --hosts "ajio.com,www.ajio.com" \
  --role "both"
```

### 2. Implement the Python Protocol
Every adapter must implement the `SourceAdapter` protocol (see `examples/adapter_template.py`):
- `id: str`: Unique machine identifier matching `sources.yaml`.
- `group: str`: `marketplaces` | `b2b` | `quickcommerce` | `signals`.
- `kind: str`: `marketplace` | `b2b` | `quickcommerce` | `search` | `social`.
- `roles: list[str]`: `sell_target` | `signal`.
- `async search(query: str, ctx: Any) -> SourceResult`
- `async suggest(query: str, ctx: Any) -> list[str]`
- `def parse(raw: str | dict[str, Any]) -> list[Item]`: Pure, deterministic function.
- `async healthcheck(ctx: Any) -> HealthReport`: Lightweight canary verification.

### 3. Apply the 5-Step Strategy Ladder
Always attempt strategies in order, stopping at the first that yields valid items:
1. **Public Suggestion/JSON API**: Lightweight HTTP GET (e.g. `completion.amazon.in` or `suggestqueries.google.com`). Fastest, zero browser overhead.
2. **Embedded State**: Extract JSON from HTML markup (`__NEXT_DATA__`, `window.__myntraState`, `window.__INITIAL_STATE__`, or `application/ld+json`).
3. **Network Interception**: Listen to `page.on("response")` for internal XHR/fetch JSON containing product lists.
4. **DOM Selectors with Fallbacks**: Use ordered CSS fallback chains if JSON is unavailable.
5. **Structural Heuristics**: Fuzzy keyword or text block extraction as an ultimate fallback.

Record `strategy_used` in the returned `SourceResult`.

### 4. Configure `sources.yaml`
Register the source in `backend/app/scrapers/sources.yaml` specifying:
- `tos_risk`: `low` | `medium` | `high`
- `relevance`: `high` | `medium` | `low`
- `hosts`: Explicit domains for the outbound SSRF allowlist (no wildcards).
- `url_templates`: Search and autosuggest URL patterns.
- `delay_min` / `delay_max`: Polite jitter delays (seconds).
- `block_images`: `true` by default, `false` only if the site breaks without images.
- `status_override`: Set `unavailable` or `disabled` with `status_reason` if no public search exists.

### 5. Health Model & Circuit Breaker
Every source maintains a health record in SQLite table `source_health`:
- **States**: `healthy` | `degraded` | `blocked` | `unavailable` | `disabled` | `unknown`.
- **Circuit Breaker**: If a source records 3 consecutive failures, the breaker opens for 30 minutes. Subsequent requests skip the source immediately, logging a warning rather than timing out.

---

## Rules

### DO
- Keep `parse()` completely pure and decoupled from Playwright or network calls so it can be tested offline against fixtures.
- Set `status_override: unavailable` with a factual explanation (e.g. "Payment platform without public product catalog") instead of scraping landing pages or faking data.
- Declare every outbound host explicitly in `sources.yaml` to ensure SSRF protection.
- Record which strategy succeeded in `SourceResult.strategy_used`.

### DON'T
- **DO NOT create a 5th agent.** All sources plug into Agent 2 (Marketplace Scraper) or Agent 3 (Social Scraper).
- **DO NOT use stealth or evasion plugins.** No `playwright-stealth`, undetected chromedriver, or proxy rotation.
- **DO NOT attempt to solve CAPTCHAs.** On bot challenge, stop immediately and return `blocked`.
- **DO NOT use Google Custom Search JSON API** (deprecated, retiring Jan 2027).

---

## Examples

### Declaring an Unavailable App-Only Source
```yaml
  - id: toing
    label: "Toing"
    group: "quickcommerce"
    kind: "quickcommerce"
    roles: ["signal"]
    default_enabled: false
    tos_risk: "low"
    relevance: "low"
    status_override: "unavailable"
    status_reason: "Food delivery app, no apparel catalog or public web search."
    hosts:
      - "toing.com"
```

---

## Checklist Before Finishing
- [ ] Adapter implements `SourceAdapter` protocol methods (`search`, `suggest`, `parse`, `healthcheck`).
- [ ] Source declared in `backend/app/scrapers/sources.yaml` with explicit host allowlist.
- [ ] 5-step strategy ladder implemented with fallbacks.
- [ ] Pure `parse` method tested against recorded canary fixture.
- [ ] No stealth tools, captcha solvers, or new agents introduced.
