---
name: playwright-marketplace-scraper
description: Coordinates polite, resilient scraping of Amazon.in, Myntra, and Flipkart using Playwright. Use when gathering live marketplace search results, fetching autosuggest phrases, parsing e-commerce product cards, or validating CSS selectors against HTML changes.
---

# Playwright Marketplace Scraper

## Purpose
This skill coordinates the automated, polite collection of organic search listings, sponsored signals, and search autosuggest completions across Amazon.in, Myntra, and Flipkart. It uses Playwright headless Chromium configured for Indian locale, applies aggressive media blocking for performance, respects rate limits with delays, and uses fallback selector registries.

> [!WARNING]
> Automated scraping may breach platform Terms of Service. The user must accept this operational risk. To minimize surface area and detection, this skill mandates querying public autosuggest API endpoints and checking local 24-hour cache before launching browser pages.

## When to use
- When the Marketplace Scraper agent executes search queries produced by the AI Planner.
- When retrieving real-time search autosuggest strings from Amazon, Myntra, or Flipkart.
- When parsing product titles, prices, ratings, and review counts for keyword extraction.
- When validating or repairing broken selectors via `scripts/selector_healthcheck.py`.
- When encountering CAPTCHA or robot-checks and needing to fail gracefully with `status="blocked"`.

## Step-by-step procedure

1. **Environment Setup & Browser Bootstrap**:
   - Dependencies: `pip install playwright pyyaml` followed by `playwright install chromium`.
   - Browser launch parameters:
     ```python
     browser = await playwright.chromium.launch(
         headless=True,
         args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
     )
     ```
   - Context settings:
     - `locale`: `"en-IN"`
     - `timezone_id`: `"Asia/Kolkata"`
     - `viewport`: `{"width": 1366, "height": 900}`
     - Realistic Desktop User-Agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36`
   - Maintain **one isolated browser context per platform** to prevent cross-site cookie leaks.

2. **Network Route Filtering**:
   - Block bandwidth-heavy resources to increase throughput by 3-5x:
     ```python
     await page.route(
         "**/*",
         lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_()
     )
     ```

3. **Check Cache & Autosuggest Endpoints First**:
   - Before firing full page navigations, check the 24h SQLite cache (`scrape:{platform}:{normalized_query}`).
   - If missing, attempt lightweight HTTP autosuggest API calls:
     - **Amazon**: `https://completion.amazon.in/api/2017/suggestions?limit=11&prefix={query}&suggestion-type=KEYWORD&mid=A21TJRUUN4KGV&alias=aps` (verify parameters via DevTools Network tab).
     - **Flipkart**: `https://www.flipkart.com/api/6/search/suggestions?q={query}`.
     - **Myntra**: `https://www.myntra.com/gateway/v2/search/suggest?query={query}`.

4. **Polite Navigation & Rate Limits**:
   - Enforce politeness rules:
     - Minimum random delay between page requests: `2.0` to `5.0` seconds.
     - Maximum 1 concurrent page per domain.
     - Maximum 2 result pages and 5 queries per platform per run.
   - For Flipkart, dismiss login modals if intercepted (e.g., clicking `button._2KpZ6l._2doB4z` or `button:has-text("✕")`).

5. **CAPTCHA & Robot-Check Detection**:
   - Check page HTML and current URL for challenge tokens:
     - Amazon: `images-amazon.com/captcha`, `Type the characters you see in this image`.
     - Flipkart: `shield.flipkart.com`, `Please verify you are a human`.
     - Myntra: `challenge-platform`, `Access Denied`.
   - **On detection**: Do NOT retry aggressively. Immediately abort the platform scrape, log `status = "blocked"`, and return any partial data collected.

6. **Selector Registry Extraction Pattern**:
   - Load `resources/selectors.yaml`.
   - **Amazon.in**:
     - Card: `div[data-component-type="s-search-result"]`
     - Title: `h2 a span`
     - Price: `span.a-price span.a-offscreen`
     - Sponsored: `span:has-text("Sponsored")` or `div.puis-sponsored-label-text`
   - **Myntra**:
     - Check for embedded state first: extract `window.__myntraState` via regex from `<script>` tags for high-fidelity structured JSON.
     - Fallback DOM Card: `li.product-base`
     - Title: `h4.product-product`
     - Brand: `h3.product-brand`
   - **Flipkart**:
     - Class names change frequently; use structural selectors: `div[data-id]`, `div:has(a[href*="/p/"])`, `a[href*="pid="]`.

7. **Standardize Output Schema**:
   - Construct Pydantic model for every product and platform summary:
     ```python
     class ScrapedProduct(BaseModel):
         title: str
         brand: str
         price: float | None = None
         mrp: float | None = None
         rating: float | None = None
         rating_count: int | None = None
         position: int
         sponsored: bool = False
         url: str
         platform: str

     class PlatformScrapeResult(BaseModel):
         platform: str
         query: str
         status: Literal["success", "blocked", "cached", "error"]
         products: list[ScrapedProduct] = []
         suggestions: list[str] = []
         related_searches: list[str] = []
     ```

## Rules (do / don't)
- **DO** verify selectors using `scripts/selector_healthcheck.py` whenever marketplace HTML structures change.
- **DO** prefer fast, lightweight autosuggest JSON endpoints before launching headless browser tabs.
- **DO** abort immediately with `status="blocked"` if a CAPTCHA or bot-check is encountered.
- **DO** isolate browser contexts per domain (one for Amazon, one for Flipkart, one for Myntra).
- **DON'T** hammer marketplace sites without delay; always enforce 2-5s random delays.
- **DON'T** exceed 2 result pages or 5 queries per platform per execution.
- **DON'T** download images, web fonts, or videos during scraping.
- **DON'T** ever attempt to bypass or solve CAPTCHAs.

## Examples

### Polite Scraper Execution Snippet
```python
import asyncio
import random
from playwright.async_api import BrowserContext

async def polite_fetch_amazon_search(context: BrowserContext, query: str) -> list[dict]:
    # Polite jitter delay
    await asyncio.sleep(random.uniform(2.0, 4.5))
    page = await context.new_page()
    try:
        await page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["image", "media", "font"] else r.continue_())
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        
        if "captcha" in page.url or "characters you see" in await page.content():
            return [] # Flag as blocked
        
        cards = await page.query_selector_all('div[data-component-type="s-search-result"]')
        # Extract title, price, sponsored attributes...
        return results
    finally:
        await page.close()
```

## Checklist before finishing
- [ ] Playwright configured with Indian locale (`en-IN`), Asia/Kolkata timezone, and 1366x900 viewport.
- [ ] Route handler intercepts and blocks images, fonts, and media.
- [ ] Random 2-5s delay and 1-page domain concurrency enforced.
- [ ] CAPTCHA triggers mark run status as `blocked` without retrying.
- [ ] Selector fallback registry (`resources/selectors.yaml`) updated and verified with `scripts/selector_healthcheck.py`.
- [ ] Autosuggest endpoints prioritized before page loads.
- [ ] Output conforms to `PlatformScrapeResult` and `ScrapedProduct` schemas.
