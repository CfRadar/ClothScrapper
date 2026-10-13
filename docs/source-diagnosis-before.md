# Source Diagnosis Before Refactor (Phase 0)

Generated at: 2026-10-04 19:05:30Z
Canary Query: `black oversized t-shirt men`

| Source | Status | Symptom | Classified Cause | Planned Fix |
|---|---|---|---|---|
| Amazon.in (`amazon`) | **HEALTHY** | 60 items found using selector 'div[data-component-type='s-search-result']' | `None` | Add embedded state and network capture as resilience fallbacks. |
| Myntra (`myntra`) | **HEALTHY** | 50 items found using selector 'li.product-base' | `None` | Add embedded state and network capture as resilience fallbacks. |
| Flipkart (`flipkart`) | **HEALTHY** | 20 items found using selector 'div._75nlfW, div[data-id]' | `None` | Add embedded state and network capture as resilience fallbacks. |
| Reddit (`reddit`) | `blocked` | HTTP 403 Blocked | `blocked` | Add realistic desktop User-Agent and token-bucket rate limiter (<=10 RPM). |
| X (Twitter) (`x`) | `degraded` | 0 cards matched despite HTTP 200 payload | `selector_drift` | Ascend strategy ladder: extract embedded JSON state or network response before falling back to DOM. |
| Instagram (`instagram`) | `blocked` | HTTP 200 or bot challenge screen | `blocked` | Never bypass. Fall back to suggestion API and 24h cache; mark blocked in health tracker. |
