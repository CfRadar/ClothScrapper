---
name: social-listener-scraper
description: Conducts social listening across Reddit fashion communities and optional best-effort social sources. Use when extracting organic shopper buzz, wish/ask phrasing, trend hashtags, and normalizing community slang into e-commerce candidate keywords using at most 1 LLM call.
---

# Social Listener Scraper

## Purpose
This skill extracts organic consumer demand signals, trending aesthetics, and "wish/ask" phrases from social media communities to discover what actual shoppers are seeking. It uses Reddit's unauthenticated public JSON endpoints with rate limiting, provides stubbed best-effort adapters for heavily gated networks (X and Instagram), and extracts high-signal consumer intent phrases while strictly capping LLM usage to at most 1 call.

## When to use
- When the Social Scraper agent runs in parallel with the Marketplace Scraper.
- When querying fashion and streetwear subreddits for T-shirt trends and style discussions.
- When extracting customer wish patterns (e.g., "looking for heavy oversized tee", "where to buy boxy tees").
- When clustering unstructured social slang and hashtags into clean candidate keywords.

## Step-by-step procedure

1. **Configure Reddit Public JSON Polling**:
   - Reddit allows unauthenticated JSON access by appending `.json` to standard URLs.
   - Global search URL:
     `https://www.reddit.com/search.json?q={encoded_query}&limit=25&sort=relevance&t=year`
   - Subreddit-specific search URL:
     `https://www.reddit.com/r/{subreddit}/search.json?q={encoded_query}&restrict_sr=1&limit=25&sort=relevance&t=year`
   - Configurable target subreddits:
     - `IndianFashionAddicts` (High-intent Indian fashion community)
     - `IndianStreetwear` (Oversized, graphic, boxy, streetwear focus)
     - `MaleFashionAdvice`
     - `femalefashionadvice`
     - `tshirts`
   - Headers: Must supply a distinctive, descriptive `User-Agent` (e.g., `User-Agent: python:marketplace-keyword-agent:v1.0 (by /u/researcher)`).
   - Rate limiting: Reddit unauthenticated API allows ~10-30 req/min. Enforce a strict maximum of **10 requests per minute** with a 2-second sleep between requests.

2. **Handle X and Instagram Gracefully (Gated Adapters)**:
   - **X (Twitter)** and **Instagram** require session authentication, employ aggressive Cloudflare/PerimeterX bot detection, and actively block scrapers.
   - Implement optional adapters controlled strictly by environment flags:
     `ENABLE_X=false`
     `ENABLE_INSTAGRAM=false`
   - If disabled (default), immediately return empty signals:
     ```python
     return SocialResult(source="x", status="skipped", signals=[])
     ```
   - If enabled and any login wall, redirect, or HTTP 401/403 is received, do NOT retry. Immediately return empty signals and mark `status="blocked_login_required"`.
   - **Never bypass logins, never automate credentials, never solve CAPTCHAs.**

3. **Heuristic Pattern Extraction (No LLM)**:
   - Parse Reddit post titles, selftext, and top comments using regex rules:
     - **Wish/Ask patterns**:
       - `r"(?:looking for|where to buy|any recommendation for|suggest|best brand for)\s+([^?.!,]+)"`
     - **Fabric & GSM mentions**:
       - `r"(\d{3}\s*gsm|french terry|heavyweight cotton|pure cotton|acid wash)"`
     - **Hashtags and style tags**:
       - `r"#([a-zA-Z0-9_]+)"`
   - Aggregate occurrences into initial signal models:
     ```python
     class SocialSignal(BaseModel):
         source: str
         phrase: str
         mentions: int
         sample_titles: list[str] = []
     ```

4. **Batch Cluster with At Most 1 LLM Call**:
   - Collect the top 30-50 raw phrases and wish strings across all subreddits.
   - If raw phrases are clean enough, pass them directly to the scoring engine.
   - If the phrases contain excessive conversational noise, execute **at most 1 LLM call** using an OpenRouter `:free` model:
     - Prompt:
       ```
       You are an e-commerce keyword extractor. Given these raw social media phrases from Indian fashion communities:
       {raw_phrases}

       Extract up to 25 distinct shopper search keywords (2-4 words) that customers would type into Amazon, Myntra, or Flipkart.
       Strip filler words, user handles, and conversational syntax.
       Output JSON format: {"keywords": ["...", "..."]}
       ```
   - Record the single LLM call against the SQLite quota guard.

## Rules (do / don't)
- **DO** use a descriptive custom `User-Agent` when querying Reddit's public `.json` endpoints.
- **DO** cap Reddit requests to at most 10 per minute to prevent 429 IP bans.
- **DO** keep X and Instagram adapters disabled by default behind explicit environment flags.
- **DO** limit the entire social extraction pipeline to **at most 1 LLM call**.
- **DON'T** store, collect, or ask for user credentials or session cookies for X, Instagram, or Reddit.
- **DON'T** attempt to bypass login walls, challenge screens, or CAPTCHA pages.
- **DON'T** flood Reddit with more than 2-3 queries per run.

## Examples

### Reddit Public JSON Polling Snippet
```python
import httpx
import re

REDDIT_SUBREDDITS = ["IndianFashionAddicts", "IndianStreetwear"]
WISH_REGEX = re.compile(r"(?:looking for|where to buy|recommend(?:ation)? for)\s+([a-zA-Z0-9\s-]{4,30})", re.IGNORECASE)

async def scrape_reddit_community(query: str) -> list[dict]:
    headers = {"User-Agent": "python:marketplace-keyword-agent:v1.0"}
    signals = []
    
    async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
        for sub in REDDIT_SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={query}&restrict_sr=1&limit=15&sort=relevance&t=year"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("children", [])
                    for post in data:
                        title = post.get("data", {}).get("title", "")
                        for match in WISH_REGEX.findall(title):
                            signals.append({"source": f"reddit/r/{sub}", "phrase": match.strip(), "title": title})
            except Exception:
                continue
    return signals
```

## Checklist before finishing
- [ ] Reddit queries use public `.json` endpoints with custom `User-Agent`.
- [ ] Subreddit list is configurable (`IndianFashionAddicts`, `IndianStreetwear`, etc.).
- [ ] X and Instagram adapters return empty lists and `skipped` status when disabled.
- [ ] Wish/ask regex patterns extract intent without LLM overhead.
- [ ] LLM normalization step consumes at most 1 call from the free budget.
- [ ] Zero credential storage or login bypass logic.
