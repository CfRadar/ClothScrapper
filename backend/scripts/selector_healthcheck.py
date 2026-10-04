#!/usr/bin/env python3
"""
backend/scripts/selector_healthcheck.py

Usage:
    python backend/scripts/selector_healthcheck.py
    python backend/scripts/selector_healthcheck.py --platform amazon
    python backend/scripts/selector_healthcheck.py --platform myntra

Description:
    Runs a live health check using Playwright against Amazon.in, Myntra, and Flipkart
    to verify that the ordered CSS and structural selectors in selectors.yaml match live markup.
"""

import argparse
import asyncio
import os
import sys

import yaml

try:
    from playwright.async_api import BrowserContext, Page, async_playwright
except ImportError:
    print(
        "[ERROR] Playwright not installed. Run: pip install playwright && playwright install chromium",
        file=sys.stderr,
    )
    sys.exit(1)

SELECTORS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "scrapers", "selectors.yaml"
)

TEST_QUERY = "men oversized cotton t shirt"


async def test_platform(platform: str, config: dict, context: BrowserContext):
    print(f"\n[*] Testing {platform.upper()} selectors...")
    page: Page = await context.new_page()
    await page.route(
        "**/*",
        lambda r: (
            r.abort() if r.request.resource_type in ["image", "media", "font"] else r.continue_()
        ),
    )

    url_template = config.get("search_url", "")
    if platform == "myntra":
        url = url_template.format(query=TEST_QUERY.replace(" ", "-"))
    else:
        url = url_template.format(query=TEST_QUERY.replace(" ", "+"))

    try:
        print(f"  Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        content = await page.content()

        # Bot check
        for token in config.get("captcha_identifiers", []):
            if token.lower() in content.lower() or token in page.url:
                print(f"  [!] BLOCKED by bot check token: '{token}'")
                await page.close()
                return

        # Modal close if flipkart
        for btn_sel in config.get("close_modal", []):
            el = await page.query_selector(btn_sel)
            if el:
                await el.click()

        # Product cards
        card_sel = None
        for sel in config.get("product_card", []):
            cards = await page.query_selector_all(sel)
            if cards:
                card_sel = sel
                print(f"  [OK] Product card selector matched: '{sel}' ({len(cards)} cards)")
                first_card = cards[0]
                break

        if not card_sel:
            print("  [FAIL] No product card selector matched!")
            await page.close()
            return

        # Fields
        for field in ["title", "brand", "price", "mrp", "rating", "rating_count"]:
            matched = False
            for sel in config.get(field, []):
                el = await first_card.query_selector(sel)
                if el:
                    val = (await el.text_content() or "").strip()
                    print(f"  [OK] {field:<14}: '{sel}' -> '{val[:25]}'")
                    matched = True
                    break
            if not matched:
                print(f"  [WARN] {field:<14}: No fallback selector matched")

    except Exception as e:
        print(f"  [ERROR] {e}")
    finally:
        await page.close()


async def main_async(selected_platform: str = None):
    if not os.path.exists(SELECTORS_PATH):
        print(f"Selectors file not found: {SELECTORS_PATH}", file=sys.stderr)
        return

    with open(SELECTORS_PATH, encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    platforms = [selected_platform] if selected_platform else list(registry.keys())

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )

        for p in platforms:
            if p in registry:
                await test_platform(p, registry[p], context)
                await asyncio.sleep(2)

        await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["amazon", "myntra", "flipkart"], default=None)
    args = parser.parse_args()
    asyncio.run(main_async(args.platform))


if __name__ == "__main__":
    main()
