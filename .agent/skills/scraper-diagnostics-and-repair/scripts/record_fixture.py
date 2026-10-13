#!/usr/bin/env python3
"""
Sanitized Fixture Recorder for Marketplace Keyword Agent Sources.
Captures live HTML or JSON payload, scrubs cookies/tokens, writes to backend/tests/fixtures/<source>/canary.html,
and checks for fixture age (>90 days warning).

Usage:
    python record_fixture.py --source amazon
"""

import argparse
import asyncio
import datetime
import os
import re
import sys
from playwright.async_api import async_playwright

FIXTURE_BASE = os.path.join("backend", "tests", "fixtures")

# Predefined canary query URLs
SOURCE_URLS = {
    "amazon": "https://www.amazon.in/s?k=oversized+t+shirt",
    "myntra": "https://www.myntra.com/oversized-t-shirt",
    "flipkart": "https://www.flipkart.com/search?q=oversized+t+shirt",
    "indiamart": "https://dir.indiamart.com/search.mp?ss=oversized+t+shirt",
    "ajio": "https://www.ajio.com/s/oversized-t-shirts",
}


def sanitize_content(content: str) -> str:
    """Removes sensitive tokens, cookies, email addresses, and tracking parameters."""
    # Redact session tokens
    content = re.sub(r'sk-or-[A-Za-z0-9_-]+', 'sk-or-REDACTED', content)
    content = re.sub(r'(token|csrf|session|auth)=["\'][^"\']+["\']', r'\1="REDACTED"', content, flags=re.I)
    # Redact potential user emails
    content = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', 'user@example.com', content)
    return content


def check_fixture_age(fixture_path: str):
    if not os.path.exists(fixture_path):
        return
    mtime = os.path.getmtime(fixture_path)
    file_date = datetime.datetime.fromtimestamp(mtime)
    age_days = (datetime.datetime.now() - file_date).days
    if age_days > 90:
        print(f"[!] WARNING: Fixture '{fixture_path}' is {age_days} days old (>90 days). Consider re-recording.")


async def record_fixture(source_id: str):
    url = SOURCE_URLS.get(source_id)
    if not url:
        print(f"[-] Error: No canary URL defined for '{source_id}'.")
        print(f"    Available: {', '.join(SOURCE_URLS.keys())}")
        sys.exit(1)

    fixture_dir = os.path.join(FIXTURE_BASE, source_id)
    os.makedirs(fixture_dir, exist_ok=True)
    fixture_file = os.path.join(fixture_dir, "canary.html")

    print(f"[*] Navigating to {url} via Playwright...")
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
            sys.exit(1)

        context = await browser.new_context(
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            content = await page.content()
            sanitized = sanitize_content(content)

            # Prepend metadata header
            now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
            header = f"<!-- FIXTURE: {source_id} | RECORDED_AT: {now} | CANARY_QUERY: oversized t shirt -->\n"
            full_data = header + sanitized

            with open(fixture_file, "w", encoding="utf-8") as f:
                f.write(full_data)

            print(f"[+] Successfully saved sanitized fixture to {fixture_file} ({len(full_data)} bytes)")
            check_fixture_age(fixture_file)

        except Exception as e:
            print(f"[-] Failed to record fixture: {e}")
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Record an offline test fixture for a scraping source")
    parser.add_argument("--source", required=True, help="Source ID (e.g. amazon, myntra, flipkart, indiamart)")
    args = parser.parse_args()
    asyncio.run(record_fixture(args.source.lower()))


if __name__ == "__main__":
    main()
