from backend.app.schemas import (
    PlatformScrape,
    ProductBrief,
    ScrapedProduct,
    SocialScrape,
    SocialSignal,
)
from backend.app.scoring.candidates import extract_candidates
from backend.app.scoring.scorer import has_conflicting_attributes, score_platform


def test_has_conflicting_attributes():
    brief = ProductBrief(platforms=["amazon"], tshirt_type="oversized tee", color="black")
    # White conflicts with black
    assert has_conflicting_attributes("white oversized t-shirt", brief) is True
    # Black does not conflict
    assert has_conflicting_attributes("black oversized t-shirt", brief) is False
    # Neutral term does not conflict
    assert has_conflicting_attributes("cotton drop shoulder t-shirt", brief) is False


def test_extract_candidates_n_grams():
    titles = [
        "Men Black Oversized Cotton T-Shirt Drop Shoulder",
        "Men Black Oversized Cotton T-Shirt Loose Fit",
    ]
    suggestions = ["oversized cotton t-shirt"]
    related = ["streetwear tee"]
    social = ["drop shoulder t-shirt"]

    candidates = extract_candidates(titles, suggestions, related, social)
    assert len(candidates) > 0
    # "oversized cotton t-shirt" appears in both titles and suggestions
    assert any("oversized" in c for c in candidates)


def test_scoring_brand_drop_and_ranking():
    brief = ProductBrief(
        platforms=["amazon"], tshirt_type="oversized graphic tee", color="black", fabric="cotton"
    )

    products = [
        ScrapedProduct(
            platform="amazon",
            title="Roadster Men Black Oversized Cotton T-Shirt",
            brand="Roadster",
            position=1,
            rating_count=5000,
            url="http://amazon.in/p1",
        ),
        ScrapedProduct(
            platform="amazon",
            title="Men Black Oversized Cotton T-Shirt",
            brand="Generic",
            position=2,
            rating_count=3000,
            url="http://amazon.in/p2",
        ),
        ScrapedProduct(
            platform="amazon",
            title="White Graphic Tee For Men",
            brand="Generic",
            position=3,
            rating_count=100,
            url="http://amazon.in/p3",
        ),
    ]

    scrape = PlatformScrape(
        platform="amazon",
        status="ok",
        products=products,
        suggestions=["black oversized cotton t-shirt", "graphic oversized t-shirt"],
        related_searches=["streetwear graphic tee"],
    )

    social = SocialScrape(
        signals=[SocialSignal(source="reddit", phrase="oversized cotton t-shirt", mentions=5)],
        candidate_keywords=["oversized cotton t-shirt"],
    )

    scored = score_platform("amazon", scrape=scrape, social=social, brief=brief)
    scored_keywords = [kw for kw, score in scored]

    # Roadster (competitor brand) should be dropped
    assert not any("roadster" in kw.lower() for kw in scored_keywords)
    # White (conflicting color) should be dropped
    assert not any("white" in kw.lower() for kw in scored_keywords)
    # High-scoring terms matching brief and suggestions should be at top
    assert len(scored) > 0
    top_term = scored[0][0]
    assert "oversized" in top_term or "black" in top_term or "cotton" in top_term
    assert 0.0 <= scored[0][1] <= 1.0


def test_scoring_fallback_when_platform_blocked():
    brief = ProductBrief(platforms=["myntra"], tshirt_type="oversized graphic tee", color="black")

    blocked_scrape = PlatformScrape(platform="myntra", status="blocked", products=[])
    other_scrape = PlatformScrape(
        platform="amazon",
        status="ok",
        products=[
            ScrapedProduct(
                platform="amazon",
                title="Men Black Oversized Graphic T-Shirt",
                brand="TopBrand",
                position=1,
                url="http://amazon.in/p1",
            )
        ],
        suggestions=["black oversized graphic t-shirt"],
    )

    scored = score_platform(
        "myntra",
        scrape=blocked_scrape,
        social=None,
        brief=brief,
        all_platform_scrapes={"amazon": other_scrape, "myntra": blocked_scrape},
    )

    assert len(scored) > 0
    # Should use the other platform's data
    assert any("graphic" in kw or "oversized" in kw for kw, score in scored)
