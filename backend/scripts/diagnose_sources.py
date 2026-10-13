#!/usr/bin/env python3
"""
Phase 0 Source Diagnostic Script
Audits existing scrapers (amazon, myntra, flipkart, reddit, x, instagram)
using canary query 'black oversized t-shirt men'.
Saves debug artifacts to backend/data/debug/<source>/<timestamp>/
and writes docs/source-diagnosis-before.md.
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

CANARY_QUERY = "black oversized t-shirt men"
DEBUG_BASE = os.path.join("backend", "data", "debug")
BEFORE_REPORT = os.path.join("docs", "source-diagnosis-before.md")

SOURCES = [
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
        "url": f"https://www.myntra.com/{quote_plus(CANARY_QUERY.replace(' ', '-'))}",
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
        "id": "reddit",
        "label": "Reddit",
        "url": f"https://www.reddit.com/r/IndianFashionAddicts/search.json?q={quote_plus(CANARY_QUERY)}&restrict_sr=1&limit=10",
        "is_api_only": True,
    },
    {
        "id": "x",
        "label": "X (Twitter)",
        "url": f"https://x.com/search?q={quote_plus(CANARY_QUERY)}&f=live",
        "card_selector": "article[data-testid='tweet']",
        "block_images": False,
    },
    {
        "id": "meesho",
        "label": "Meesho",
        "url": f"https://www.meesho.com/search?q={quote_plus(CANARY_QUERY)}",
        "card_selector": "div[class*='ProductList__GridCol'], div[class*='Card__BaseCard'], div[data-testid='product-card']",
        "block_images": False,
    },
    {
        "id": "instagram",
        "label": "Instagram",
        "url": "https://www.instagram.com/explore/tags/blackoversizedtshirt/",
        "card_selector": "article a, div._aagv",
        "block_images": False,
    },
]


def classify_failure(html: str, status_code: int | None, network_events: list[dict], console_logs: list[str]) -> tuple[str, str, str]:
    """
    Returns (symptom, cause, planned_fix)
    """
    lower = html.lower()

    if status_code in (403, 429) or "enter the characters you see below" in lower or "captcha" in lower or "robot check" in lower:
        return (
            f"HTTP {status_code} or bot challenge screen",
            "blocked",
            "Never bypass. Fall back to suggestion API and 24h cache; mark blocked in health tracker."
        )

    if "login" in lower and ("sign in to" in lower or "log in to" in lower or "phone number, username, or email" in lower):
        return (
            "Forced authentication barrier",
            "login_wall",
            "Walled garden. Stop immediately at login wall; keep adapter off by default."
        )

    if "select your location" in lower or "enter pincode" in lower or ("deliver to" in lower and "pincode" in lower):
        return (
            "Location modal obscuring page",
            "consent_or_location_modal",
            "Add modal dismiss selector in sources.yaml; inject DELIVERY_PINCODE if required."
        )

    if status_code == 404:
        return (
            "HTTP 404 Not Found",
            "wrong_url",
            "Correct search URL template in sources.yaml."
        )

    if len(html) < 2500:
        return (
            "Empty or stub HTML payload (<2.5KB)",
            "timing",
            "Move to strategy ladder: network capture or explicit container wait instead of networkidle."
        )

    return (
        "0 cards matched despite HTTP 200 payload",
        "selector_drift",
        "Ascend strategy ladder: extract embedded JSON state or network response before falling back to DOM."
    )


async def diagnose():
    print(f"=== Phase 0: Live Scraper Diagnostics (Canary: '{CANARY_QUERY}') ===")
    os.makedirs(DEBUG_BASE, exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    findings = []

    async with async_playwright() as p:
        browser = None
        for ch in ["chrome", "msedge", None]:
            try:
                browser = await p.chromium.launch(channel=ch, headless=True)
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

        for src in SOURCES:
            source_id = src["id"]
            label = src["label"]
            print(f"\n[*] Probing {label} ({source_id})...")
            start_t = time.time()
            out_dir = os.path.join(DEBUG_BASE, source_id, timestamp)
            os.makedirs(out_dir, exist_ok=True)

            status = "unknown"
            items_found = 0
            suggestions_found = 0
            symptom = "Normal execution"
            cause = "None"
            planned_fix = "None needed"

            # 1. API Probing
            suggest_url = src.get("suggest_url")
            if suggest_url:
                try:
                    p_api = await context.new_page()
                    r_api = await p_api.goto(suggest_url, timeout=12000)
                    if r_api and r_api.status == 200:
                        txt = await r_api.text()
                        with open(os.path.join(out_dir, "suggest.json"), "w", encoding="utf-8") as f:
                            f.write(txt)
                        try:
                            d = json.loads(txt)
                            if isinstance(d, list) and len(d) > 1 and isinstance(d[1], list):
                                suggestions_found = len(d[1])
                            elif isinstance(d, dict):
                                suggestions_found = len(d.get("suggestions", d.get("data", [])))
                        except Exception:
                            pass
                    await p_api.close()
                except Exception as e:
                    print(f"    [!] Suggestion probe error: {e}")

            if src.get("is_api_only"):
                # Handle pure API sources like Reddit
                try:
                    p_api = await context.new_page()
                    r_api = await p_api.goto(src["url"], timeout=15000)
                    status_code = r_api.status if r_api else None
                    raw_text = await r_api.text() if r_api else ""
                    with open(os.path.join(out_dir, "response.json"), "w", encoding="utf-8") as f:
                        f.write(raw_text)
                    await p_api.close()

                    if status_code == 200 and "data" in raw_text:
                        status = "healthy"
                        symptom = "JSON posts returned"
                        cause = "None"
                        planned_fix = "Maintain public JSON endpoint parser with custom User-Agent."
                    elif status_code in (403, 429):
                        status = "blocked"
                        symptom = f"HTTP {status_code} Blocked"
                        cause = "blocked"
                        planned_fix = "Add realistic desktop User-Agent and token-bucket rate limiter (<=10 RPM)."
                    else:
                        status = "degraded"
                        symptom = f"HTTP {status_code}"
                        cause = "timing"
                        planned_fix = "Verify endpoint format and parameters."
                except Exception as e:
                    status = "blocked" if "403" in str(e) else "degraded"
                    symptom = f"Fetch error: {str(e)[:80]}"
                    cause = "blocked" if "403" in str(e) else "timing"
                    planned_fix = "Wrap in try-except with safe fallback."

                findings.append({
                    "source": label, "id": source_id, "status": status,
                    "symptom": symptom, "cause": cause, "fix": planned_fix
                })
                continue

            # 2. Browser Search Probing
            page = await context.new_page()
            console_logs = []
            network_events = []

            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

            def on_resp(resp):
                try:
                    ct = resp.headers.get("content-type", "")
                    if "json" in ct:
                        network_events.append({"url": resp.url[:120], "status": resp.status})
                except Exception:
                    pass

            page.on("response", on_resp)

            if src.get("block_images"):
                await page.route("**/*.{png,jpg,jpeg,webp,svg,gif}", lambda r: r.abort())

            try:
                resp = await page.goto(src["url"], wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(3.0)  # Allow lazy JS to execute

                html = await page.content()
                status_code = resp.status if resp else None

                # Save debug artifacts
                with open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                await page.screenshot(path=os.path.join(out_dir, "screenshot.png"))
                with open(os.path.join(out_dir, "console.json"), "w", encoding="utf-8") as f:
                    json.dump(console_logs, f, indent=2)
                with open(os.path.join(out_dir, "network.json"), "w", encoding="utf-8") as f:
                    json.dump(network_events, f, indent=2)

                card_sel = src.get("card_selector", "")
                if card_sel:
                    cards = await page.locator(card_sel).count()
                    items_found = cards

                if items_found > 0:
                    status = "healthy"
                    symptom = f"{items_found} items found using selector '{card_sel}'"
                    cause = "None"
                    planned_fix = "Add embedded state and network capture as resilience fallbacks."
                else:
                    symptom, cause, planned_fix = classify_failure(html, status_code, network_events, console_logs)
                    status = "blocked" if cause in ("blocked", "login_wall") else "degraded"

            except Exception as e:
                status = "blocked" if "Timeout" in str(e) else "degraded"
                symptom = f"Navigation failed: {str(e)[:100]}"
                cause = "blocked" if "Timeout" in str(e) else "timing"
                planned_fix = "Implement circuit breaker and fallback to suggestion API."

            await page.close()

            findings.append({
                "source": label, "id": source_id, "status": status,
                "symptom": symptom, "cause": cause, "fix": planned_fix
            })

        await browser.close()

    # Write docs/source-diagnosis-before.md
    with open(BEFORE_REPORT, "w", encoding="utf-8") as f:
        f.write("# Source Diagnosis Before Refactor (Phase 0)\n\n")
        f.write(f"Generated at: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')}\n")
        f.write(f"Canary Query: `{CANARY_QUERY}`\n\n")
        f.write("| Source | Status | Symptom | Classified Cause | Planned Fix |\n")
        f.write("|---|---|---|---|---|\n")
        for f_item in findings:
            stat_badge = f"**{f_item['status'].upper()}**" if f_item["status"] == "healthy" else f"`{f_item['status']}`"
            f.write(f"| {f_item['source']} (`{f_item['id']}`) | {stat_badge} | {f_item['symptom']} | `{f_item['cause']}` | {f_item['fix']} |\n")

    print(f"\n[+] Findings successfully compiled to {BEFORE_REPORT}")


if __name__ == "__main__":
    asyncio.run(diagnose())
