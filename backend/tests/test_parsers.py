import os

from backend.app.scrapers.amazon import parse_amazon_autosuggest
from backend.app.scrapers.amazon import parse_related_searches as parse_amazon_related
from backend.app.scrapers.amazon import parse_search_html as parse_amazon_html
from backend.app.scrapers.flipkart import parse_search_html as parse_flipkart_html
from backend.app.scrapers.myntra import parse_search_html as parse_myntra_html

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_amazon_pure_parser():
    with open(os.path.join(FIXTURE_DIR, "amazon_search.html"), encoding="utf-8") as f:
        html = f.read()

    products = parse_amazon_html(html)
    assert len(products) == 2

    p1 = products[0]
    assert p1.platform == "amazon"
    assert "Men Black Oversized Cotton" in p1.title
    assert p1.brand == "Veirdo"
    assert p1.price == 599.0
    assert p1.mrp == 1199.0
    assert p1.rating == 4.3
    assert p1.rating_count == 2410
    assert p1.sponsored is True
    assert p1.position == 1

    p2 = products[1]
    assert p2.brand == "Bonkers Corner"
    assert p2.price == 799.0
    assert p2.sponsored is False

    related = parse_amazon_related(html)
    assert "oversized streetwear tee" in related


def test_amazon_autosuggest_parser():
    data = {
        "suggestions": [
            {"value": "oversized t shirt for men"},
            {"value": "oversized t shirt cotton"},
        ]
    }
    suggestions = parse_amazon_autosuggest(data)
    assert suggestions == ["oversized t shirt for men", "oversized t shirt cotton"]


def test_myntra_pure_parser_embedded_state():
    with open(os.path.join(FIXTURE_DIR, "myntra_search.html"), encoding="utf-8") as f:
        html = f.read()

    products = parse_myntra_html(html)
    assert len(products) == 2

    p1 = products[0]
    assert p1.platform == "myntra"
    assert p1.brand == "Roadster"
    assert "Pure Cotton Oversized" in p1.title
    assert p1.price == 549.0
    assert p1.mrp == 1299.0
    assert p1.rating == 4.2
    assert p1.rating_count == 3400
    assert p1.sponsored is False

    p2 = products[1]
    assert p2.brand == "HRX"
    assert p2.sponsored is True


def test_flipkart_pure_parser():
    with open(os.path.join(FIXTURE_DIR, "flipkart_search.html"), encoding="utf-8") as f:
        html = f.read()

    products = parse_flipkart_html(html)
    assert len(products) == 2

    p1 = products[0]
    assert p1.platform == "flipkart"
    assert p1.brand == "TripCity"
    assert "Men Solid Oversized Pure Cotton" in p1.title
    assert p1.price == 449.0
    assert p1.rating == 4.1
    assert p1.rating_count == 1820

    p2 = products[1]
    assert p2.brand == "Bullmer"
    assert p2.price == 389.0
