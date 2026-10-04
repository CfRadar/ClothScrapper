import re
import urllib.parse

import httpx
from backend.app.config import get_settings
from backend.app.schemas import PlatformScrape, ScrapedProduct, SearchPlan
from backend.app.scrapers.browser import BrowserManager
from bs4 import BeautifulSoup

AUTOSUGGEST_URL = "https://completion.amazon.in/api/2017/suggestions?limit=11&prefix={prefix}&suggestion-type=KEYWORD&mid=A21TJRUUN4KGV&alias=aps"


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    # Extract digits and decimal point, e.g. "₹499.00" -> 499.0
    clean = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(clean) if clean else None
    except ValueError:
        return None


def parse_rating(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(\.\d+)?)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_int(text: str | None) -> int | None:
    if not text:
        return None
    clean = re.sub(r"[^\d]", "", text)
    try:
        return int(clean) if clean else None
    except ValueError:
        return None


def parse_search_html(html: str) -> list[ScrapedProduct]:
    """Pure parser function converting Amazon search result HTML into ScrapedProduct models."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('div[data-component-type="s-search-result"]')
    products: list[ScrapedProduct] = []

    for idx, card in enumerate(cards, 1):
        # 1. Title
        title_elem = (
            card.select_one("h2 a span") or card.select_one("h2 span") or card.select_one("h2 a")
        )
        title = title_elem.get_text(strip=True) if title_elem else ""
        if not title:
            continue

        # 2. Brand
        brand_elem = (
            card.select_one("h5.s-line-clamp-1 span")
            or card.select_one("span.a-size-base-plus.a-color-base")
            or card.select_one(".s-line-clamp-1")
        )
        brand = brand_elem.get_text(strip=True) if brand_elem else None

        # 3. Price
        price_elem = card.select_one("span.a-price span.a-offscreen") or card.select_one(
            "span.a-price-whole"
        )
        price = parse_price(price_elem.get_text(strip=True) if price_elem else None)

        # 4. MRP
        mrp_elem = card.select_one("span.a-price.a-text-price span.a-offscreen") or card.select_one(
            "span.a-text-strike"
        )
        mrp = parse_price(mrp_elem.get_text(strip=True) if mrp_elem else None)

        # 5. Rating & Count
        rating_elem = card.select_one("i.a-icon-star-small span.a-icon-alt") or card.select_one(
            "span.a-icon-alt"
        )
        rating = parse_rating(rating_elem.get_text(strip=True) if rating_elem else None)

        count_elem = card.select_one("span.a-size-base.s-underline-text") or card.select_one(
            'a[href*="customerReviews"] span'
        )
        rating_count = parse_int(count_elem.get_text(strip=True) if count_elem else None)

        # 6. Sponsored
        is_sponsored = "sponsored" in card.get_text(separator=" ", strip=True).lower()

        # 7. URL
        link_elem = card.select_one("h2 a")
        href = link_elem.get("href", "") if link_elem else ""
        full_url = urllib.parse.urljoin("https://www.amazon.in", href)

        products.append(
            ScrapedProduct(
                platform="amazon",
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
    elements = soup.select(
        'div[data-component-type="s-keyword-latent-search"] a, div.s-desktop-toolbar a[href*="field-keywords"]'
    )
    related = []
    for el in elements:
        text = el.get_text(strip=True)
        if text and text not in related:
            related.append(text)
    return related


def parse_amazon_autosuggest(data: dict) -> list[str]:
    suggestions = []
    for item in data.get("suggestions", []):
        val = item.get("value", "")
        if val and val not in suggestions:
            suggestions.append(val)
    return suggestions


async def autosuggest(query: str) -> list[str]:
    """Fetch public autosuggest keywords for Amazon India via HTTP."""
    encoded = urllib.parse.quote_plus(query)
    url = AUTOSUGGEST_URL.format(prefix=encoded)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return parse_amazon_autosuggest(resp.json())
    except Exception:
        pass
    return []


async def search(query: str, plan: SearchPlan, browser_mgr: BrowserManager) -> PlatformScrape:
    """Scrape search results from Amazon.in using Playwright."""
    settings = get_settings()
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.amazon.in/s?k={encoded}"

    context = await browser_mgr.get_context("amazon")
    page = await context.new_page()

    try:
        is_blocked, content = await browser_mgr.polite_goto(page, url, platform="amazon")
        if is_blocked:
            return PlatformScrape(
                platform="amazon",
                status="blocked",
                products=[],
                suggestions=await autosuggest(query),
                note="Amazon robot check / CAPTCHA triggered.",
            )

        products = parse_search_html(content)[: settings.MAX_PRODUCTS_PER_QUERY]
        related = parse_related_searches(content)
        suggestions = await autosuggest(query)

        return PlatformScrape(
            platform="amazon",
            status="ok" if products else "partial",
            products=products,
            suggestions=suggestions,
            related_searches=related,
        )
    except Exception as e:
        return PlatformScrape(
            platform="amazon",
            status="error",
            products=[],
            suggestions=[],
            note=str(e),
        )
    finally:
        await page.close()
