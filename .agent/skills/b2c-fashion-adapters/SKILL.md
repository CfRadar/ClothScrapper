---
name: b2c-fashion-adapters
description: Technical playbooks, selector hints, embedded state schemas, and popup handlers for Indian B2C fashion marketplaces including Amazon.in, Myntra, Flipkart, Ajio, and Snapmint. Trigger when repairing or building B2C retail scraping adapters.
---

# B2C Fashion Adapters

## Purpose
Provides concrete implementation playbooks for the core Indian B2C e-commerce retail fashion platforms. Details URL patterns, embedded JSON state paths, network interception points, lazy-loading thresholds, and modal dismiss logic.

> [!IMPORTANT]
> All selectors, CSS paths, and API endpoints documented here are **starting hints**. Every selector must be verified live in the Playwright browser during implementation before being committed to production.

---

## When to Use
- Implementing or repairing adapters for **Amazon.in**, **Myntra**, **Flipkart**, or **Ajio**.
- Registering partner payment and catalog platforms like **Snapmint**.
- Standardizing product card extraction into normalized `Item` objects.

---

## Standard Output Model

All B2C adapters must return listings normalized into the `Item` model:

```python
class Item(BaseModel):
    title: str
    brand: str = ""
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int = 0
    sponsored: bool = False
    url: str = ""
    source_id: str
```

---

## Platform Playbooks

### 1. Amazon.in (`amazon`)
- **Search URL**: `https://www.amazon.in/s?k={query}`
- **Autosuggest Endpoint (Strategy 1)**:
  `https://completion.amazon.in/api/2017/suggestions?limit=11&prefix={query}&suggestion-type=KEYWORD&mid=A21TJRUUN4KGV&alias=aps`
- **Result Container**: `div[data-component-type='s-search-result']`
- **Field Selectors**:
  - Title: `h2 a span`, `h2.a-size-mini span`
  - Brand: `h5.s-line-clamp-1 span`, `.a-row .a-size-base-plus`
  - Price: `span.a-price-whole` (strip commas)
  - MRP: `span.a-price.a-text-price span.a-offscreen`
  - Rating: `span[aria-label*='out of 5 stars']`
  - Rating Count: `span[aria-label*='out of 5 stars'] + span` or `a span.a-size-base`
  - Sponsored Marker: `span.puis-sponsored-label-text`, `span:has-text('Sponsored')`
- **Popup Handling**: Location/pincode prompt dismissed by clicking `input[data-action-type='DISMISS']` or backdrop.
- **Lazy Loading**: Bottom search pagination and sponsored carousel require scrolling 1200px.

---

### 2. Myntra (`myntra`)
- **Search URL**: `https://www.myntra.com/{query}` (slugified query, e.g. `oversized-t-shirts`)
- **Autosuggest Endpoint (Strategy 1)**:
  `https://www.myntra.com/gateway/v2/search/suggest?query={query}`
- **Embedded State (Strategy 2)**:
  Inspect page script tags: `window.__myntraState = JSON.parse(...)`. Contains `searchData.results.products` array with exact price, brand, rating, and discounts.
- **DOM Fallback (Strategy 4)**:
  - Card: `li.product-base`
  - Brand: `h3.product-brand`
  - Title: `h4.product-product`
  - Price: `span.product-discountedPrice`, `div.product-price span`
  - MRP: `span.product-strike`
  - Rating: `div.product-ratingsContainer span`
- **Lazy Loading**: Myntra uses infinite scroll. Step-scroll (`scrollBy(0, 1000)`) twice to load at least 24 products.

---

### 3. Flipkart (`flipkart`)
- **Search URL**: `https://www.flipkart.com/search?q={query}`
- **Autosuggest Endpoint (Strategy 1)**:
  `https://www.flipkart.com/api/6/search/suggestions?q={query}`
- **Modal Dismiss**:
  Flipkart frequently displays an unauthenticated login popup on initial load. Dismiss with:
  ```python
  close_btn = page.locator("button:has-text('✕'), span[role='button']:has-text('✕')")
  if await close_btn.count() > 0:
      await close_btn.first.click()
  ```
- **Field Selectors**:
  - Card: `div._75nlfW`, `div[data-id]`, `div._1xHGtK`
  - Title: `a.WKTcLC`, `a.IRpwTa`, `div._2WkVRV`
  - Brand: `div._2WkVRV`
  - Price: `div.Nx93G0`, `div._30jeq3`
  - MRP: `div.yRaY8j`, `div._3I9_wc`
  - Rating: `div.XQDdHH`, `div._3LWZlK`
  - Sponsored: `div._4rR01T:has-text('Ad')`, `span:has-text('Sponsored')`

---

### 4. Ajio (`ajio`)
- **Nature**: Complex React Single Page Application (SPA). DOM scraping is brittle due to heavily obfuscated, frequently hashed emotion/styled-components CSS classes.
- **Search URL**: `https://www.ajio.com/s/{query}`
- **Recommended Strategy**: **Strategy 3 (Network Capture)**:
  Intercept internal search API:
  `page.on("response", handler)` matching `api/search?text={query}` or `api/category/...`. The response payload returns an array of `products` with structured metadata:
  ```json
  {
    "fnlColorVariantData": { "brandName": "Netplay", "outOfStock": false },
    "name": "Typographic Print Pure Cotton T-Shirt",
    "price": { "value": 499.0, "formattedValue": "Rs. 499" },
    "wasPriceData": { "value": 999.0 }
  }
  ```
- **DOM Fallback**:
  - Container: `div.items, div.rilrtl-products-list`
  - Card: `div.item`
  - Brand: `div.brand`
  - Title: `div.name`
  - Price: `span.price`

---

### 5. Snapmint (`snapmint`)
- **Platform Reality**: Snapmint is an Indian consumer financing, EMI, and BNPL payment gateway partnering with merchants. It does **not** maintain an open, searchable public retail apparel catalog on the web.
- **Configuration Rule**:
  Do **not** fabricate fake search results or scrape unrelated checkout portals. Register Snapmint in `sources.yaml` with explicit status override:
  ```yaml
  - id: snapmint
    label: "Snapmint"
    group: "marketplaces"
    kind: "marketplace"
    roles: ["sell_target"]
    default_enabled: false
    tos_risk: "low"
    relevance: "low"
    status_override: "unavailable"
    status_reason: "EMI payment platform without public product search catalog"
    hosts:
      - "snapmint.com"
      - "www.snapmint.com"
  ```

---

## Rules (DO / DON'T)

### DO
- Test network capture on Ajio before writing CSS selectors.
- Always sanitize titles and strip control characters.
- Dismiss Flipkart's login modal asynchronously on page load.
- Extract `Item.brand` separately from `Item.title` to enable competitor brand filtering.

### DON'T
- DO NOT invent selectors without viewing live HTML or screenshots.
- DO NOT bypass login screens if a site blocks unauthenticated searches.
- DO NOT fake search results for payment apps (e.g. Snapmint).

---

## Checklist Before Finishing
- [ ] Verified search URL template live in browser.
- [ ] Implemented modal dismiss handlers for popups (location, login prompt).
- [ ] Extracted items verified into the normalized `Item` Pydantic model.
- [ ] Offline canary fixture recorded in `backend/tests/fixtures/<source>/`.
- [ ] Parser tests pass without network requests.
