import json
import math
import os

from backend.app.schemas import (
    PlatformName,
    PlatformScrape,
    ProductBrief,
    ScrapedProduct,
    SearchPlan,
    SocialScrape,
)
from backend.app.scoring.candidates import extract_candidates, normalize_text

RESOURCE_DIR = os.path.join(os.path.dirname(__file__), "resources")


def load_taxonomy() -> dict:
    path = os.path.join(RESOURCE_DIR, "tshirt_taxonomy.json")
    if not os.path.exists(path):
        return {"colors": ["black", "white", "blue", "red", "green", "yellow", "grey"]}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


TAXONOMY = load_taxonomy()
ALL_KNOWN_COLORS = set(TAXONOMY.get("colors", []))


def min_max_normalize(values: dict[str, float]) -> dict[str, float]:
    """Normalize a dictionary of float values to 0.0 - 1.0."""
    if not values:
        return {}
    v_min = min(values.values())
    v_max = max(values.values())
    if math.isclose(v_max, v_min):
        return {k: (1.0 if v_max > 0 else 0.0) for k in values}
    denom = v_max - v_min
    return {k: (v - v_min) / denom for k, v in values.items()}


def has_conflicting_attributes(candidate: str, brief: ProductBrief) -> bool:
    """Check if candidate conflicts with brief (e.g. brief says 'black' but candidate says 'white')."""
    cand_tokens = set(candidate.lower().split())
    brief_color = normalize_text(brief.color)
    brief_color_tokens = set(brief_color.split())

    # Detect color conflicts
    for c in ALL_KNOWN_COLORS:
        c_lower = c.lower()
        if c_lower in cand_tokens and c_lower not in brief_color_tokens:
            return True

    return False


def contains_scraped_brand(candidate: str, scraped_brands: set[str]) -> bool:
    """Check if candidate contains a trademarked competitor brand name."""
    cand_lower = candidate.lower()
    for brand in scraped_brands:
        if brand and len(brand) >= 3 and brand in cand_lower:
            return True
    return False


def score_platform(
    platform: PlatformName,
    scrape: PlatformScrape | None,
    social: SocialScrape | None,
    brief: ProductBrief,
    all_platform_scrapes: dict[PlatformName, PlatformScrape] | None = None,
    top_n: int = 60,
) -> list[tuple[str, float]]:
    """
    Deterministically scores keyword candidates for a platform.
    Formula:
      score = 0.35*suggest_presence
            + 0.25*title_freq_top10
            + 0.20*rank_weighted_reviews
            + 0.10*social_mentions
            + 0.10*attribute_match_to_brief
    """
    is_blocked_or_empty = not scrape or scrape.status in ("blocked", "error") or not scrape.products

    # Collect products and suggestions
    products: list[ScrapedProduct] = []
    suggestions: list[str] = []
    related: list[str] = []

    if not is_blocked_or_empty and scrape:
        products = scrape.products
        suggestions = scrape.suggestions
        related = scrape.related_searches
    elif all_platform_scrapes:
        # Fallback to data from other non-blocked platforms
        for p_name, other_scrape in all_platform_scrapes.items():
            if other_scrape and other_scrape.status in ("ok", "cached") and other_scrape.products:
                products.extend(other_scrape.products[:15])
                suggestions.extend(other_scrape.suggestions)
                related.extend(other_scrape.related_searches)

    # Social phrases
    social_phrases: list[str] = []
    if social:
        social_phrases.extend(social.candidate_keywords)
        social_phrases.extend([s.phrase for s in social.signals])

    # Extract brands to drop
    scraped_brands = {
        p.brand.lower().strip() for p in products if p.brand and len(p.brand.strip()) >= 3
    }
    if brief.brand_name:
        scraped_brands.discard(brief.brand_name.lower().strip())

    # Candidate pool
    product_titles = [p.title for p in products]
    candidates = extract_candidates(product_titles, suggestions, related, social_phrases)

    # Brief attribute tokens
    brief_text = f"{brief.tshirt_type} {brief.color} {brief.fit or ''} {brief.fabric or ''} {brief.neck or ''} {brief.sleeve or ''} {brief.print_or_design or ''} {brief.occasion or ''}"
    brief_tokens = {t for t in normalize_text(brief_text).split() if len(t) >= 2}

    # Filter out junk candidates
    filtered_candidates: list[str] = []
    for c in candidates:
        if len(c) < 2 or c.isdigit():
            continue
        if contains_scraped_brand(c, scraped_brands):
            continue
        if has_conflicting_attributes(c, brief):
            continue
        filtered_candidates.append(c)

    if not filtered_candidates:
        # Emergency fallback: derive directly from brief
        fallback_seeds = [
            brief.tshirt_type.lower(),
            f"{brief.color.lower()} {brief.tshirt_type.lower()}",
        ]
        return [(s, 0.5) for s in fallback_seeds]

    # Feature metrics
    suggest_presence: dict[str, float] = {}
    title_freq_top10: dict[str, float] = {}
    rank_weighted_reviews: dict[str, float] = {}
    social_mentions: dict[str, float] = {}
    attribute_match: dict[str, float] = {}

    lower_suggestions = [s.lower() for s in suggestions + related]
    top_10_products = sorted(products, key=lambda p: p.position)[:10]

    for c in filtered_candidates:
        # 1. Suggest presence
        suggest_presence[c] = 1.0 if any(c in s for s in lower_suggestions) else 0.0

        # 2. Title frequency in top 10
        title_freq_top10[c] = sum(1.0 for p in top_10_products if c in p.title.lower())

        # 3. Rank weighted reviews: sum( (1 / position) * log(reviews + 1) )
        review_score = 0.0
        for p in products:
            if c in p.title.lower():
                pos = max(1, p.position)
                revs = max(0, p.rating_count or 0)
                review_score += (1.0 / math.sqrt(pos)) * math.log1p(revs)
        rank_weighted_reviews[c] = review_score

        # 4. Social mentions
        social_mentions[c] = sum(
            float(sig.mentions)
            for sig in (social.signals if social else [])
            if c in sig.phrase.lower()
        )

        # 5. Attribute match to brief
        cand_words = set(c.split())
        overlap = len(cand_words.intersection(brief_tokens))
        attribute_match[c] = float(overlap)

    # Normalize each component
    norm_suggest = min_max_normalize(suggest_presence)
    norm_title = min_max_normalize(title_freq_top10)
    norm_reviews = min_max_normalize(rank_weighted_reviews)
    norm_social = min_max_normalize(social_mentions)
    norm_attr = min_max_normalize(attribute_match)

    scored: list[tuple[str, float]] = []
    for c in filtered_candidates:
        score = (
            0.35 * norm_suggest.get(c, 0.0)
            + 0.25 * norm_title.get(c, 0.0)
            + 0.20 * norm_reviews.get(c, 0.0)
            + 0.10 * norm_social.get(c, 0.0)
            + 0.10 * norm_attr.get(c, 0.0)
        )
        scored.append((c, round(score, 4)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_n]


def score_all(
    brief: ProductBrief,
    plan: SearchPlan,
    marketplace_scrapes: dict[PlatformName, PlatformScrape],
    social: SocialScrape | None,
) -> dict[PlatformName, list[tuple[str, float]]]:
    """Score candidates for every requested platform."""
    results: dict[PlatformName, list[tuple[str, float]]] = {}
    for platform in brief.platforms:
        scrape = marketplace_scrapes.get(platform)
        results[platform] = score_platform(
            platform=platform,
            scrape=scrape,
            social=social,
            brief=brief,
            all_platform_scrapes=marketplace_scrapes,
        )
    return results
