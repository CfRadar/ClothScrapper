import asyncio
import re
import urllib.parse

import httpx
from backend.app.config import get_settings
from backend.app.schemas import PlatformScrape, ScrapedProduct, SearchPlan
from backend.app.scrapers.browser import BrowserManager
from bs4 import BeautifulSoup

AUTOSUGGEST_URL = "https://www.flipkart.com/api/6/search/suggestions?q={query}"


def parse_price_regex(text: str) -> float | None:
    match = re.search(r"₹\s*([\d,]+)", text)
    if match:
        digits = match.group(1).replace(",", "")
        try:
            return float(digits)
        except ValueError:
            return None
    return None


def parse_rating_regex(text: str) -> float | None:
    match = re.search(r"\b([1-5]\.\d)\b", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_search_html(html: str) -> list[ScrapedProduct]:
    """
    Structural parser for Flipkart's frequently changing and obfuscated CSS classes.
    Finds product cards with data-id or anchors targeting product links (/p/ or pid=).
    """
    soup = BeautifulSoup(html, "html.parser")
    # Identify product cards by structural patterns
    cards = soup.select("div[data-id]")
    if not cards:
        cards = [
            a.parent
            for a in soup.select('a[href*="/p/"]')
            if a.parent and len(a.parent.get_text()) > 30
        ]

    products: list[ScrapedProduct] = []

    for idx, card in enumerate(cards, 1):
        # 1. Product Link
        link = card.select_one('a[href*="/p/"]') or card.select_one('a[href*="pid="]')
        href = link.get("href", "") if link else ""
        if not href:
            continue
        full_url = urllib.parse.urljoin("https://www.flipkart.com", href)

        # 2. Title from link title attribute, img alt, or longest text
        title = ""
        if link and link.get("title"):
            title = link.get("title", "").strip()
        if not title:
            img = card.select_one("img[alt]")
            if img and img.get("alt"):
                title = img.get("alt", "").strip()
        if not title and link:
            title = link.get_text(strip=True)

        if not title or len(title) < 3:
            continue

        # 3. Brand
        brand_elem = card.select_one("div._2WkVRV, div.syl9yP")
        brand = brand_elem.get_text(strip=True) if brand_elem else None
        if not brand and " " in title:
            brand = title.split()[0]

        card_text = card.get_text(separator=" ", strip=True)

        # 4. Price & MRP via Regex
        price = parse_price_regex(card_text)
        # Search for multiple prices (discounted + MRP)
        all_prices = re.findall(r"₹\s*([\d,]+)", card_text)
        mrp = None
        if len(all_prices) >= 2:
            try:
                mrp_val = float(all_prices[1].replace(",", ""))
                if price and mrp_val > price:
                    mrp = mrp_val
            except Exception:
                pass

        # 5. Rating & Count
        rating = parse_rating_regex(card_text)
        rating_count = None
        count_match = re.search(r"\((\d[\d,]*)\)", card_text)
        if count_match:
            try:
                rating_count = int(count_match.group(1).replace(",", ""))
            except Exception:
                pass

        # 6. Sponsored
        is_sponsored = "sponsored" in card_text.lower()

        products.append(
            ScrapedProduct(
                platform="flipkart",
                title=title,
                brand=brand,
                price=price,
                mrp=mrp,
                rating=rating,
                rating_count=rating_count,
                position=idx,
                sponsored=is_sponsored,
                url=full_url,
            )
        )

    return products


def parse_related_searches(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select("div._10Ermr a, div._3GI52j a")
    related = []
    for el in elements:
        text = el.get_text(strip=True)
        if text and text not in related:
            related.append(text)
    return related


def parse_flipkart_autosuggest(data: dict) -> list[str]:
    suggestions = []
    for query_item in data.get("queries", []):
        word = query_item.get("query")
        if word and word not in suggestions:
            suggestions.append(word)
    return suggestions


async def autosuggest(query: str) -> list[str]:
    """Fetch autosuggest keywords from Flipkart API."""
    encoded = urllib.parse.quote_plus(query)
    url = AUTOSUGGEST_URL.format(query=encoded)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return parse_flipkart_autosuggest(resp.json())
    except Exception:
        pass
    return []


async def search(query: str, plan: SearchPlan, browser_mgr: BrowserManager) -> PlatformScrape:
    """Scrape search results from Flipkart using Playwright."""
    settings = get_settings()
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.flipkart.com/search?q={encoded}"

    context = await browser_mgr.get_context("flipkart")
    page = await context.new_page()

    try:
        # Dismiss login modal if present
        page.on(
            "load",
            lambda: asyncio.create_task(
                page.locator("button:has-text('✕')").click().catch(lambda _: None)
            ),
        )

        is_blocked, content = await browser_mgr.polite_goto(page, url, platform="flipkart")
        if is_blocked:
            return PlatformScrape(
                platform="flipkart",
                status="blocked",
                products=[],
                suggestions=await autosuggest(query),
                note="Flipkart robot check / shield triggered.",
            )

        products = parse_search_html(content)[: settings.MAX_PRODUCTS_PER_QUERY]
        related = parse_related_searches(content)
        suggestions = await autosuggest(query)

        return PlatformScrape(
            platform="flipkart",
            status="ok" if products else "partial",
            products=products,
            suggestions=suggestions,
            related_searches=related,
        )
    except Exception as e:
        return PlatformScrape(
            platform="flipkart",
            status="error",
            products=[],
            suggestions=[],
            note=str(e),
        )
    finally:
        await page.close()
