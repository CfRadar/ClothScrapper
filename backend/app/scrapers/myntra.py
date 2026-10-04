import json
import re
import urllib.parse

import httpx
from backend.app.config import get_settings
from backend.app.schemas import PlatformScrape, ScrapedProduct, SearchPlan
from backend.app.scrapers.browser import BrowserManager
from bs4 import BeautifulSoup

AUTOSUGGEST_URL = "https://www.myntra.com/gateway/v2/search/suggest?query={query}"


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    clean = re.sub(r"[^\d.]", "", text.replace(",", ""))
    try:
        return float(clean) if clean else None
    except ValueError:
        return None


def parse_search_html(html: str) -> list[ScrapedProduct]:
    """
    Parses Myntra search HTML into ScrapedProduct models.
    First attempts to extract structured embedded state window.__myntraState;
    falls back to DOM parsing if state is absent.
    """
    products: list[ScrapedProduct] = []

    # 1. Try parsing window.__myntraState
    state_match = re.search(r"window\.__myntraState\s*=\s*(\{.*?\});", html, re.DOTALL)
    if state_match:
        try:
            state_data = json.loads(state_match.group(1))
            items = state_data.get("searchData", {}).get("results", {}).get("products", [])
            for idx, item in enumerate(items, 1):
                brand = item.get("brand", "")
                prod = item.get("product", "")
                extra = item.get("additionalInfo", "")
                title = f"{brand} {prod} {extra}".strip()
                p_url = item.get("landingPageUrl", "")
                full_url = urllib.parse.urljoin("https://www.myntra.com/", p_url)
                products.append(
                    ScrapedProduct(
                        platform="myntra",
                        title=title or "T-Shirt",
                        brand=item.get("brand"),
                        price=float(item.get("price", 0)) if item.get("price") else None,
                        mrp=float(item.get("mrp", 0)) if item.get("mrp") else None,
                        rating=float(item.get("rating", 0)) if item.get("rating") else None,
                        rating_count=int(item.get("ratingCount", 0))
                        if item.get("ratingCount")
                        else None,
                        position=idx,
                        sponsored=bool(item.get("isAd")),
                        url=full_url,
                    )
                )
            if products:
                return products
        except Exception:
            pass

    # 2. DOM parsing fallback
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li.product-base, div.product-card")

    for idx, card in enumerate(cards, 1):
        brand_elem = card.select_one("h3.product-brand")
        name_elem = card.select_one("h4.product-product") or card.select_one(
            "h3.product-brand + h4"
        )

        brand = brand_elem.get_text(strip=True) if brand_elem else None
        name = name_elem.get_text(strip=True) if name_elem else ""
        title = f"{brand or ''} {name}".strip()
        if not title:
            continue

        price_elem = card.select_one("span.product-discountedPrice") or card.select_one(
            "div.product-price span"
        )
        price = parse_price(price_elem.get_text(strip=True) if price_elem else None)

        mrp_elem = card.select_one("span.product-strike")
        mrp = parse_price(mrp_elem.get_text(strip=True) if mrp_elem else None)

        rating_elem = card.select_one("div.product-ratingsContainer span")
        rating = None
        if rating_elem:
            try:
                rating = float(rating_elem.get_text(strip=True).split()[0])
            except Exception:
                pass

        count_elem = card.select_one("div.product-ratingsCount")
        rating_count = None
        if count_elem:
            digits = re.sub(r"[^\d]", "", count_elem.get_text(strip=True))
            rating_count = int(digits) if digits else None

        is_sponsored = bool(card.select_one("span.product-adLabel"))
        link_elem = card.select_one("a[href]")
        href = link_elem.get("href", "") if link_elem else ""
        full_url = urllib.parse.urljoin("https://www.myntra.com/", href)

        products.append(
            ScrapedProduct(
                platform="myntra",
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
    elements = soup.select("div.search-hints a, div.breadcrumbs-container a")
    related = []
    for el in elements:
        text = el.get_text(strip=True)
        if text and len(text) > 3 and text not in related:
            related.append(text)
    return related


def parse_myntra_autosuggest(data: dict) -> list[str]:
    suggestions = []
    # Myntra suggest response format
    for item in data.get("data", []) or data.get("suggestions", []):
        word = item.get("keyword") or item.get("query") or item.get("value")
        if word and word not in suggestions:
            suggestions.append(word)
    return suggestions


async def autosuggest(query: str) -> list[str]:
    """Fetch autosuggest keywords from Myntra gateway API."""
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
                return parse_myntra_autosuggest(resp.json())
    except Exception:
        pass
    return []


async def search(query: str, plan: SearchPlan, browser_mgr: BrowserManager) -> PlatformScrape:
    """Scrape search results from Myntra using Playwright."""
    settings = get_settings()
    hyphen_query = query.replace(" ", "-")
    url = f"https://www.myntra.com/{hyphen_query}?rawQuery={urllib.parse.quote_plus(query)}"

    context = await browser_mgr.get_context("myntra")
    page = await context.new_page()

    try:
        is_blocked, content = await browser_mgr.polite_goto(page, url, platform="myntra")
        if is_blocked:
            return PlatformScrape(
                platform="myntra",
                status="blocked",
                products=[],
                suggestions=await autosuggest(query),
                note="Myntra challenge / bot check triggered.",
            )

        products = parse_search_html(content)[: settings.MAX_PRODUCTS_PER_QUERY]
        related = parse_related_searches(content)
        suggestions = await autosuggest(query)

        return PlatformScrape(
            platform="myntra",
            status="ok" if products else "partial",
            products=products,
            suggestions=suggestions,
            related_searches=related,
        )
    except Exception as e:
        return PlatformScrape(
            platform="myntra",
            status="error",
            products=[],
            suggestions=[],
            note=str(e),
        )
    finally:
        await page.close()
