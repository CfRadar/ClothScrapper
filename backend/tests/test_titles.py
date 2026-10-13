import pytest
from backend.app.schemas import ProductBrief, TitlePart
from backend.app.titles.builder import build_fallback_titles, load_rules
from backend.app.titles.composer import compose_title
from backend.app.titles.validator import validate_and_compose_title


@pytest.fixture
def sample_brief() -> ProductBrief:
    return ProductBrief(
        platforms=["amazon", "myntra", "flipkart", "meesho"],
        tshirt_type="oversized graphic t-shirt",
        color="black",
        gender="men",
        fit="drop shoulder relaxed fit",
        fabric="100% cotton, 240 GSM",
        neck="round neck",
        sleeve="half sleeve",
        print_or_design="acid wash back print",
        occasion="casual streetwear",
        brand_name="UrbanAura",
        pack="pack of 1",
    )


@pytest.fixture
def sample_brief_no_brand_no_fabric() -> ProductBrief:
    return ProductBrief(
        platforms=["amazon", "myntra", "flipkart", "meesho"],
        tshirt_type="regular t-shirt",
        color="navy blue",
        gender="women",
        fit="regular fit",
        neck="v neck",
        brand_name=None,
        fabric=None,
    )


def test_composer_formula_order_and_deduplication():
    rules = load_rules()
    parts = [
        TitlePart(label="color", text="Black"),
        TitlePart(label="gender", text="Men"),
        TitlePart(label="type", text="T-Shirt"),
        TitlePart(label="brand", text="UrbanAura"),
        TitlePart(label="fit", text="Oversized Fit"),
        # duplicate token
        TitlePart(label="feature", text="Black Graphic"),
    ]
    # Amazon formula: brand, gender, type, fit, neck, sleeve, pattern, fabric, color, feature, pack
    text, ordered = compose_title(parts, "amazon", rules)

    assert ordered[0].label == "brand"
    assert "UrbanAura" in text
    # Check that "Black" is not duplicated
    tokens = text.lower().split()
    assert tokens.count("black") == 1
    assert "T-Shirt" in text


def test_validator_drops_unprovided_brand(sample_brief_no_brand_no_fabric):
    rules = load_rules()
    parts = [
        TitlePart(label="brand", text="Nike"),
        TitlePart(label="gender", text="Women"),
        TitlePart(label="color", text="Navy Blue"),
        TitlePart(label="type", text="T-Shirt"),
    ]
    title = validate_and_compose_title(
        parts,
        style="short",
        platform="amazon",
        brief=sample_brief_no_brand_no_fabric,
        platform_keywords=["women t shirt"],
        rules=rules,
    )
    assert "Nike" not in title.text
    assert any("unprovided brand" in w.lower() for w in title.warnings)


def test_validator_drops_unsupported_material_claim(sample_brief_no_brand_no_fabric):
    rules = load_rules()
    parts = [
        TitlePart(label="gender", text="Women"),
        TitlePart(label="fabric", text="100% Pure Organic Cotton 240 GSM"),
        TitlePart(label="color", text="Navy Blue"),
        TitlePart(label="type", text="T-Shirt"),
    ]
    title = validate_and_compose_title(
        parts,
        style="balanced",
        platform="amazon",
        brief=sample_brief_no_brand_no_fabric,
        platform_keywords=["cotton t shirt"],
        rules=rules,
    )
    # Since fabric was None in sample_brief_no_brand_no_fabric, cotton / 240 GSM is unsupported
    assert "cotton" not in title.text.lower()
    assert any("unsupported claim" in w.lower() for w in title.warnings)


def test_validator_drops_forbidden_promotional_words(sample_brief):
    rules = load_rules()
    parts = [
        TitlePart(label="brand", text="UrbanAura"),
        TitlePart(label="feature", text="#1 Best Selling Top Rated Discount"),
        TitlePart(label="type", text="T-Shirt"),
    ]
    title = validate_and_compose_title(
        parts,
        style="search",
        platform="amazon",
        brief=sample_brief,
        platform_keywords=["best t shirt"],
        rules=rules,
    )
    assert "best" not in title.text.lower()
    assert "#1" not in title.text
    assert "discount" not in title.text.lower()


def test_validator_prunes_overlength_parts(sample_brief):
    rules = load_rules()
    # Amazon hard_max is 200, Myntra hard_max is 100
    parts = [
        TitlePart(label="brand", text="UrbanAura"),
        TitlePart(label="gender", text="Men"),
        TitlePart(label="color", text="Black"),
        TitlePart(label="pattern", text="Super Heavy Acid Wash Hand Crafted Typography Graphic Print"),
        TitlePart(label="fit", text="Relaxed Drop Shoulder Boxy Heavyweight Fit"),
        TitlePart(label="type", text="Oversized T-Shirt"),
        TitlePart(label="fabric", text="100% Combed Heavy Cotton 240 GSM"),
    ]
    # For Myntra (hard_max = 100)
    title = validate_and_compose_title(
        parts,
        style="search",
        platform="myntra",
        brief=sample_brief,
        platform_keywords=["black oversized t shirt"],
        rules=rules,
    )
    assert len(title.text) <= 100
    # Must never drop type or color
    assert "T-Shirt" in title.text or "Oversized" in title.text
    assert "Black" in title.text


def test_fallback_builder_all_platforms(sample_brief):
    rules = load_rules()
    for plat in ["amazon", "myntra", "flipkart", "meesho"]:
        titles = build_fallback_titles(plat, sample_brief, ["oversized tee", "cotton tee"], rules=rules)
        assert len(titles) == 3
        styles = [t.style for t in titles]
        assert styles == ["search", "balanced", "short"]
        for t in titles:
            assert t.length > 0
            assert t.length <= t.hard_max
            assert "UrbanAura" in t.text
            assert "Black" in t.text
            assert "T-Shirt" in t.text or "Tee" in t.text


def test_extract_top_scraped_titles(sample_brief):
    from backend.app.schemas import PlatformScrape, ScrapedProduct
    from backend.app.titles.curated_titles import extract_top_scraped_titles

    # 1. Without live products - extracts top 10 adapted from curated database
    titles = extract_top_scraped_titles("amazon", sample_brief, None)
    assert len(titles) == 10
    assert titles[0].rank == 1
    assert titles[9].rank == 10
    for t in titles:
        assert t.title
        assert t.length == len(t.title)
        assert t.brand

    # 2. With live scraped products
    live_scrape = PlatformScrape(
        platform="amazon",
        status="ok",
        products=[
            ScrapedProduct(
                platform="amazon",
                title="Live Scraped Brand Men Oversized Black Graphic Tee 240 GSM",
                brand="LiveBrand",
                price=799.0,
                rating=4.5,
                position=1,
                url="https://amazon.in/dp/test",
            )
        ],
    )
    live_titles = extract_top_scraped_titles("amazon", sample_brief, live_scrape)
    assert len(live_titles) == 10
    assert live_titles[0].rank == 1
    assert "Live Scraped Brand" in live_titles[0].title
    assert live_titles[0].brand == "LiveBrand"
    assert "799" in (live_titles[0].price or "")
    assert live_titles[0].rating == 4.5

