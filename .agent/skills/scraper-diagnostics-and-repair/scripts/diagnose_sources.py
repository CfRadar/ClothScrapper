#!/usr/bin/env python3
"""
Diagnostic Canary Runner for Marketplace Keyword Agent Sources.
Runs canary queries, captures debug artifacts (screenshot, HTML, sanitized network events),
classifies failure causes, and outputs source-health.md.

Usage:
    python diagnose_sources.py [--headed] [--only <source_id>]
"""

import argparse
import asyncio
import datetime
import json
import os
import sys
import time
from urllib.parse import quote_plus
from playwright.async_api import async_playwright

CANARY_QUERY = "oversized t shirt"
DEBUG_BASE = os.path.join("backend", "data", "debug")
HEALTH_REPORT = "source-health.md"

# Default Sources for Canary testing
CANARY_SOURCES = [
    {
        "id": "amazon",
        "label": "Amazon.in",
        "url": f"https://www.amazon.in/s?k={quote_plus(CANARY_QUERY)}",
        "suggest_url": f"https://completion.amazon.in/api/2017/suggestions?limit=11&prefix={quote_plus(CANARY_QUERY)}&suggestion-type=KEYWORD&mid=A21TJRUUN4KGV&alias=aps",
        "card_selector": "div[data-component-type='s-search-result']",
        "block_images": True,
    },
    {
        "id": "myntra",
        "label": "Myntra",
        "url": f"https://www.myntra.com/{quote_plus(CANARY_QUERY)}",
        "suggest_url": f"https://www.myntra.com/gateway/v2/search/suggest?query={quote_plus(CANARY_QUERY)}",
        "card_selector": "li.product-base",
        "block_images": True,
    },
    {
        "id": "flipkart",
        "label": "Flipkart",
        "url": f"https://www.flipkart.com/search?q={quote_plus(CANARY_QUERY)}",
        "suggest_url": f"https://www.flipkart.com/api/6/search/suggestions?q={quote_plus(CANARY_QUERY)}",
        "card_selector": "div._75nlfW, div[data-id]",
        "block_images": True,
    },
    {
        "id": "google_suggest",
        "label": "Google Autocomplete",
        "suggest_url": f"https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=in&q={quote_plus(CANARY_QUERY)}",
        "is_api_only": True,
    },
    {
        "id": "reddit",
        "label": "Reddit Fashion",
        "url": f"https://www.reddit.com/r/IndianFashionAddicts/search.json?q={quote_plus(CANARY_QUERY)}&restrict_sr=1&limit=10",
        "is_api_only": True,
    },
]


def classify_failure(html: str, status_code: int | None, network_events: list[dict]) -> tuple[str, str]:
    """
    Classifies failure cause according to the failure taxonomy:
    blocked | consent_or_location_modal | login_wall | lazy_load | timing | selector_drift | wrong_url | resource_blocking | rate_limited
    """
    lower = html.lower()

    if status_code in (403, 429) or "enter the characters you see below" in lower or "captcha" in lower or "robot check" in lower:
        return "blocked", "Robot check or bot shield triggered (HTTP 403/429 or CAPTCHA page detected). Do not attempt bypass."

    if "login" in lower and ("sign in to continue" in lower or "enter password" in lower or "phone number" in lower):
        return "login_wall", "Walled garden forced authentication wall. Verify if public unauthenticated view exists."

    if "select your location" in lower or "enter pincode" in lower or "deliver to" in lower and "pincode" in lower:
        return "consent_or_location_modal", "Location / pincode selection modal blocking content. Supply DELIVERY_PINCODE."

    if status_code == 404:
        return "wrong_url", "URL template returned 404 Not Found. Update search path template."

    if len(html) < 2000:
        return "timing", "Page payload suspiciously small (<2KB). Wait for explicit container rather than domcontentloaded."

    return "selector_drift", "Page loaded successfully but selectors matched 0 items. Elevate to embedded JSON or network capture."


async def run_diagnostics(sources: list[dict], headed: bool = False):
    print(f"=== Running Scraper Diagnostics ({len(sources)} sources) ===")
    results = []
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = None
        # Prefer system chrome/msedge channel
        for ch in ["chrome", "msedge", None]:
            try:
                browser = await p.chromium.launch(channel=ch, headless=not headed)
                break
            except Exception:
                continue

        if not browser:
            print("[-] Error: Unable to launch Playwright browser.")
            return

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 900},
        )

        for src in sources:
            source_id = src["id"]
            label = src["label"]
            print(f"\n[*] Auditing [{source_id}] ({label})...")
            start_time = time.time()
            out_dir = os.path.join(DEBUG_BASE, source_id, timestamp)
            os.makedirs(out_dir, exist_ok=True)

            status = "unknown"
            strategy = "none"
            items_found = 0
            suggestions_found = 0
            cause = "None"
            recommended_fix = "None needed"

            # 1. Test Suggestion / Public JSON Endpoint if present
            suggest_url = src.get("suggest_url")
            if suggest_url:
                try:
                    page_api = await context.new_page()
                    resp = await page_api.goto(suggest_url, timeout=10000)
                    if resp and resp.status == 200:
                        text = await resp.text()
                        with open(os.path.join(out_dir, "suggest.json"), "w", encoding="utf-8") as f:
                            f.write(text)
                        try:
                            data = json.loads(text)
                            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                                suggestions_found = len(data[1])
                            elif isinstance(data, dict):
                                suggestions_found = len(data.get("suggestions", data.get("data", [])))
                        except Exception:
                            pass
                    await page_api.close()
                except Exception as e:
                    print(f"    [!] Suggestion probe error: {e}")

            if src.get("is_api_only"):
                duration = round(time.time() - start_time, 2)
                if suggestions_found > 0:
                    status = "healthy"
                    strategy = "suggestion_api"
                else:
                    status = "degraded"
                    cause = "empty_response"
                    recommended_fix = "Check query encoding or IP block"
                results.append({
                    "id": source_id, "label": label, "status": status,
                    "strategy": strategy, "items": 0, "suggestions": suggestions_found,
                    "cause": cause, "duration": f"{duration}s", "fix": recommended_fix
                })
                continue

            # 2. Browser Search Audit
            network_events = []
            page = await context.new_page()

            if src.get("block_images"):
                await page.route("**/*.{png,jpg,jpeg,webp,svg,gif}", lambda r: r.abort())

            # Log network responses without auth headers
            def handle_response(response):
                try:
                    if "json" in response.headers.get("content-type", ""):
                        network_events.append({"url": response.url, "status": response.status})
                except Exception:
                    pass

            page.on("response", handle_response)

            try:
                resp = await page.goto(src["url"], wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(2.5)  # Allow dynamic content to load

                html = await page.content()
                status_code = resp.status if resp else None

                # Save debug artifacts
                with open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                await page.screenshot(path=os.path.join(out_dir, "screenshot.png"))
                with open(os.path.join(out_dir, "network.json"), "w", encoding="utf-8") as f:
                    json.dump(network_events, f, indent=2)

                # Check Selectors
                card_sel = src.get("card_selector", "")
                if card_sel:
                    cards = await page.locator(card_sel).count()
                    items_found = cards

                duration = round(time.time() - start_time, 2)

                if items_found > 0:
                    status = "healthy"
                    strategy = "dom_selector"
                else:
                    status = "degraded"
                    cause, recommended_fix = classify_failure(html, status_code, network_events)

            except Exception as e:
                duration = round(time.time() - start_time, 2)
                status = "blocked" if "Timeout" in str(e) else "degraded"
                cause = f"Exception: {str(e)[:120]}"
                recommended_fix = "Check network connectivity or raise navigation timeout"

            await page.close()

            results.append({
                "id": source_id,
                "label": label,
                "status": status,
                "strategy": strategy,
                "items": items_found,
                "suggestions": suggestions_found,
                "cause": cause,
                "duration": f"{duration}s",
                "fix": recommended_fix,
            })

        await browser.close()

    # Write Markdown Report
    with open(HEALTH_REPORT, "w", encoding="utf-8") as f:
        f.write("# Source Health & Diagnostics Report\n\n")
        f.write(f"Generated at: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}\n\n")
        f.write("| Source | Status | Strategy | Items Found | Suggestions | Cause | Duration | Recommended Fix |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in results:
            stat_str = f"**{r['status'].upper()}**" if r["status"] == "healthy" else f"`{r['status']}`"
            f.write(f"| {r['label']} (`{r['id']}`) | {stat_str} | `{r['strategy']}` | {r['items']} | {r['suggestions']} | {r['cause']} | {r['duration']} | {r['fix']} |\n")

    print(f"\n[+] Wrote diagnostics report to {HEALTH_REPORT}")


def main():
    parser = argparse.ArgumentParser(description="Audit and diagnose scraping sources")
    parser.add_argument("--headed", action="store_true", help="Run browser in visible mode")
    parser.add_argument("--only", type=str, help="Audit only a specific source ID")
    args = parser.parse_args()

    sources = CANARY_SOURCES
    if args.only:
        sources = [s for s in CANARY_SOURCES if s["id"] == args.only.lower()]
        if not sources:
            print(f"[-] Source '{args.only}' not found in registry canary list.")
            sys.exit(1)

    asyncio.run(run_diagnostics(sources, headed=args.headed))


if __name__ == "__main__":
    main()
