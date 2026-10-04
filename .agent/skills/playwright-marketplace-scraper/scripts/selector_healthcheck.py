#!/usr/bin/env python3
"""
scripts/selector_healthcheck.py

Usage:
    python scripts/selector_healthcheck.py
    python scripts/selector_healthcheck.py --platform amazon
    python scripts/selector_healthcheck.py --platform myntra --headless False

Description:
    Runs a live health check using Playwright against Amazon.in, Myntra, and Flipkart
    to verify that the ordered CSS/structural selectors defined in resources/selectors.yaml
    are still matching live marketplace HTML markup.

    Reports:
      - Network status and CAPTCHA detection
      - Matching status for product cards, titles, prices, ratings, and sponsored labels
      - First active selector found per field

Requirements:
    pip install playwright pyyaml
    playwright install chromium
"""

import os
import sys
import yaml
import asyncio
import argparse
from typing import Dict, Any

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    print("[ERROR] Playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

SELECTORS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "selectors.yaml"
)

TEST_QUERY = "men oversized cotton t shirt"

async def test_platform_selectors(platform_name: str, config: Dict[str, Any], context: BrowserContext) -> Dict[str, Any]:
    print(f"\n[*] Testing platform: {platform_name.upper()}...")
    page: Page = await context.new_page()
    
    # Block heavy media assets to minimize bandwidth and speed up check
    await page.route(
        "**/*",
        lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_()
    )

    url_template = config.get("search_url", "")
    if platform_name == "myntra":
        formatted_query = TEST_QUERY.replace(" ", "-")
        target_url = url_template.format(query=formatted_query)
    else:
        target_url = url_template.format(query=TEST_QUERY.replace(" ", "+"))

    results = {
        "platform": platform_name,
        "url": target_url,
        "blocked": False,
        "matched_selectors": {},
        "missing_selectors": []
    }

    try:
        print(f"  Navigating to: {target_url}")
        resp = await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
        status_code = resp.status if resp else 0
        results["status_code"] = status_code

        # 1. Check for CAPTCHA / bot walls
        page_content = await page.content()
        for captcha_token in config.get("captcha_identifiers", []):
            if captcha_token.lower() in page_content.lower() or captcha_token in page.url:
                print(f"  [!] BLOCKED: Detected CAPTCHA identifier: '{captcha_token}'")
                results["blocked"] = True
                await page.close()
                return results

        # 2. Check modal closure (Flipkart login popup)
        for modal_sel in config.get("close_modal", []):
            modal_btn = await page.query_selector(modal_sel)
            if modal_btn:
                try:
                    await modal_btn.click()
                    print(f"  Closed modal using selector: {modal_sel}")
                except Exception:
                    pass

        # 3. Test Product Card selectors
        card_matched_selector = None
        for sel in config.get("product_card", []):
            cards = await page.query_selector_all(sel)
            if cards:
                card_matched_selector = sel
                results["matched_selectors"]["product_card"] = f"{sel} ({len(cards)} items found)"
                first_card = cards[0]
                break

        if not card_matched_selector:
            results["missing_selectors"].append("product_card")
            print("  [!] Failed to match any product_card selectors.")
            await page.close()
            return results

        # 4. Test Sub-element selectors on the first matched product card
        fields_to_test = ["title", "brand", "price", "mrp", "rating", "rating_count", "sponsored"]
        for field in fields_to_test:
            selectors = config.get(field, [])
            matched = False
            for sel in selectors:
                el = await first_card.query_selector(sel)
                if el:
                    text_val = (await el.text_content() or "").strip()
                    results["matched_selectors"][field] = f"{sel} -> '{text_val[:30]}'"
                    matched = True
                    break
            if not matched:
                results["missing_selectors"].append(field)

    except Exception as e:
        print(f"  [!] Error testing {platform_name}: {e}")
        results["error"] = str(e)
    finally:
        await page.close()

    return results

async def main_async(selected_platform: str = None, headless: bool = True):
    if not os.path.exists(SELECTORS_PATH):
        print(f"[ERROR] selectors.yaml not found at {SELECTORS_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(SELECTORS_PATH, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    platforms_to_test = [selected_platform] if selected_platform else list(registry.keys())

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        all_results = []
        for p in platforms_to_test:
            if p in registry:
                res = await test_platform_selectors(p, registry[p], context)
                all_results.append(res)
                await asyncio.sleep(2)  # Polite gap between platforms

        await browser.close()

    print("\n" + "=" * 80)
    print("SELECTOR HEALTHCHECK SUMMARY REPORT")
    print("=" * 80)
    for r in all_results:
        p = r["platform"].upper()
        if r.get("blocked"):
            print(f"[{p}] BLOCKED (Robot Check / CAPTCHA detected)")
            continue
        print(f"[{p}] HTTP {r.get('status_code', 'N/A')}:")
        for f, val in r.get("matched_selectors", {}).items():
            print(f"  OK   {f:<15} : {val}")
        for missing in r.get("missing_selectors", []):
            print(f"  FAIL {missing:<15} : No fallback selectors matched!")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Test marketplace scraping selectors against live pages.")
    parser.add_argument("--platform", choices=["amazon", "myntra", "flipkart"], default=None, help="Specific platform to test")
    parser.add_argument("--headless", type=bool, default=True, help="Run headless or windowed")
    args = parser.parse_args()

    asyncio.run(main_async(args.platform, args.headless))

if __name__ == "__main__":
    main()
