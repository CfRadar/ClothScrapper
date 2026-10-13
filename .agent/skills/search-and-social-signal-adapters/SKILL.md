---
name: search-and-social-signal-adapters
description: Technical playbooks for signal providers feeding Agent 3 including Google autocomplete, Google Trends, SERP providers, Pinterest, Meta Ad Library, Reddit, X, and Instagram. Trigger when configuring or repairing social listening and search signal adapters.
---

# Search and Social Signal Adapters

## Purpose
Governs signal-gathering adapters that feed organic shopper buzz, wish/ask phrases, and ad copy trends into **Agent 3 (Social Scraper)**. These sources do not sell merchandise directly; they supply consumer demand signals to inform keyword ranking.

---

## When to Use
- Managing signal sources in the "Search and social" canvas group.
- Extracting autocomplete queries from Google's public endpoint.
- Scraping public Meta Ad Library copy or Pinterest style trends.
- Integrating third-party SERP providers (Brave, Serper).

---

## Standard Output Model

All signal adapters normalize findings into the `SocialSignal` Pydantic model:

```python
class SocialSignal(BaseModel):
    source: str        # google_suggest | pinterest | meta_ads | reddit | x | instagram
    phrase: str
    mentions: int = 1
    samples: list[str] = Field(default_factory=list)
```

> [!WARNING]
> All text harvested from search autocomplete, social posts, and ad copy is **untrusted external data**. Every string must be sanitized, wrapped in `<untrusted_data>` fences before LLM processing, and filtered through `gate_keywords()`.

---

## Platform Playbooks

### 1. Google Search Signals (`google_suggest`)
- **Primary Endpoint (Strategy 1)**:
  Use Google's public autocomplete endpoint:
  ```http
  GET https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=in&q={query}
  ```
  Returns a lightweight JSON array:
  `["oversized t shirt", ["oversized t shirts for men", "oversized t shirt combo", "oversized t shirt styling", ...]]`
- **Query Expansion**:
  Expand each seed keyword using at most **8 requests per run**:
  - `{seed} for men`
  - `{seed} oversized`
  - `{seed} combo pack`
  - `{seed} pure cotton`
  - `{seed} aesthetic streetwear`
- **Google Trends (Optional)**:
  Best-effort Playwright search for related topics on `trends.google.com/trends/explore?geo=IN&q={seed}`. Disabled by default.
- **Third-Party SERP Integration**:
  Configurable via `SEARCH_PROVIDER=none|brave|serper` in `backend/.env` with user-supplied key for "People also ask" and related queries.
- **Critical Policy Guardrail**:
  > [!CAUTION]
  > **DO NOT use Google's Custom Search JSON API.** It is closed to new customers and scheduled for full retirement on **1 January 2027**.
  > Direct scraping of `google.com/search` is opt-in (`ENABLE_GOOGLE_SERP_SCRAPE=false`). Encountering any `/sorry/` redirect or CAPTCHA means **immediate termination** (`status="blocked"`).

---

### 2. Pinterest Trends (`pinterest`)
- **Use Case**: Identifying visual style aesthetics, silhouette trends, and Gen-Z fashion adjectives.
- **Search Target**:
  Public search: `https://www.pinterest.com/search/pins/?q={query}` and Pinterest Trends India (`trends.pinterest.com/?country=IN`).
- **Rule**:
  Extract trend pill tags and board titles from the first screen only.
  **Stop immediately at any login modal.** Never attempt automated login. No user credentials permitted.

---

### 3. Meta Ad Library (`meta_ads`)
- **Target**: Public Meta Ad Library:
  `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=IN&q={query}`
- **Purpose**: Harvest high-converting ad headlines, hook phrases, and promotion copy used by active Indian direct-to-consumer (D2C) brands.
- **Configuration**:
  - `tos_risk: "high"`
  - `default_enabled: false` (requires explicit user toggle).
- **Rule**:
  Scrape only public, unauthenticated ad cards. Stop immediately if blocked by login or checkpoint. Never automate login.

---

### 4. Reddit Fashion Communities (`reddit`)
- **Target Subreddits**:
  `r/IndianFashionAddicts`, `r/IndianStreetwear`, `r/MaleFashionAdvice`, `r/femalefashionadvice`, `r/tshirts`.
- **Method**:
  Public JSON API (lightweight HTTP GET):
  `https://www.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=1&sort=relevance&limit=25`
  Append custom User-Agent: `MarketplaceKeywordAgent/2.0 (by /u/ecommerce_researcher)`.
- **Extraction**: Extract post titles, question phrases ("where can I find...", "best brand for..."), and user reviews.

---

### 5. X (`x`) and Instagram (`instagram`)
- **Role**: Best-effort visual and viral hashtag discovery.
- **Status**: Disabled by default behind `ENABLE_X=false` and `ENABLE_INSTAGRAM=false`.
- **Operation**:
  If public hashtag pages (`instagram.com/explore/tags/{tag}/` or `x.com/search?q={tag}`) trigger login screens, mark `skipped` with detail "Adapter disabled" or "Login wall encountered".

---

## Rules (DO / DON'T)

### DO
- Cap Google autocomplete expansion requests at $\le 8$ queries per run.
- Use `suggestqueries.google.com` (public, fast, zero browser overhead).
- Enclose all scraped social copy inside `<untrusted_data>` blocks.
- Require `tos_risk: high` acknowledgment before enabling Meta Ad Library.

### DON'T
- DO NOT use Google Custom Search JSON API (retiring Jan 2027).
- DO NOT scrape `google.com` search results unless `ENABLE_GOOGLE_SERP_SCRAPE=true`.
- DO NOT bypass login walls on Pinterest or Facebook.
- DO NOT store or automate credentials for social networks.

---

## Checklist Before Finishing
- [ ] Google autocomplete endpoint tested and verified live.
- [ ] No references to deprecated Google Custom Search JSON API.
- [ ] Pinterest and Meta Ad Library configured with immediate login-wall stops.
- [ ] Social signals normalized into `SocialSignal` model.
- [ ] Untrusted text fences applied to all extracted phrases.
