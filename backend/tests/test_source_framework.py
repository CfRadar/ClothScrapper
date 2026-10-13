import os
import pytest
import tempfile
from pathlib import Path

from backend.app.scrapers.registry import (
    load_registry,
    get_source_spec,
    get_allowlisted_hosts,
    SourceSpec,
)
from backend.app.scrapers.health import (
    record_health,
    get_source_health,
    is_circuit_breaker_open,
    map_result_status_to_health,
)
from backend.app.scrapers.query_adapters import (
    adapt_queries,
    adapt_queries_for_b2b,
    adapt_queries_for_quickcommerce,
    adapt_queries_for_signals,
)
from backend.app.scrapers.strategies.dom_selectors import parse_dom
from backend.app.scrapers.strategies.heuristics import parse_heuristics
from backend.app.scrapers.strategies.embedded_json import extract_embedded_json
from backend.app.scrapers.base import Item, SourceResult, B2BInfo


def test_sources_yaml_loads_and_validates():
    registry = load_registry(force_reload=True)
    assert len(registry.sources) >= 19
    source_ids = {s.id for s in registry.sources}
    expected_ids = {
        "amazon", "myntra", "flipkart", "ajio", "snapmint",
        "indiamart", "exportersindia", "alibaba",
        "blinkit", "swiggy_instamart", "zepto", "toing", "estay",
        "google", "pinterest", "facebook", "reddit", "x", "instagram"
    }
    for eid in expected_ids:
        assert eid in source_ids, f"Expected source {eid} missing from sources.yaml"


def test_registry_security_rules():
    # Attempting to declare a high risk source as default_enabled must fail validation
    with pytest.raises(ValueError, match="cannot be default_enabled"):
        SourceSpec(
            id="risky_source",
            label="Risky Source",
            group="B2B",
            kind="b2b",
            tos_risk="high",
            default_enabled=True,
            hosts=["example.com"],
        )

    # Attempting wildcards in hosts must fail validation
    with pytest.raises(ValueError, match="wildcards, schemes, and paths are forbidden"):
        SourceSpec(
            id="bad_host",
            label="Bad Host",
            group="Custom",
            kind="marketplace",
            hosts=["*.example.com"],
        )


def test_allowlisted_hosts():
    hosts = get_allowlisted_hosts()
    assert "openrouter.ai" in hosts
    assert "www.amazon.in" in hosts or "amazon.in" in hosts
    assert "www.myntra.com" in hosts or "myntra.com" in hosts
    assert "suggestqueries.google.com" in hosts
    # Ensure no schemes or slashes in allowlist
    for h in hosts:
        assert "://" not in h
        assert "/" not in h


@pytest.mark.asyncio
async def test_health_and_circuit_breaker():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        from backend.app.db import init_db
        await init_db(temp_db)

        # 1. Successful check
        h1 = await record_health("amazon", "ok", strategy_used="dom_selectors", db_path=temp_db)
        assert h1.status == "healthy"
        assert h1.consecutive_failures == 0
        assert not await is_circuit_breaker_open("amazon", db_path=temp_db)

        # 2. Consecutive failures
        await record_health("test_source", "error", failure_cause="timeout", db_path=temp_db)
        await record_health("test_source", "error", failure_cause="timeout", db_path=temp_db)
        h3 = await record_health("test_source", "error", failure_cause="timeout", db_path=temp_db)

        assert h3.consecutive_failures == 3
        assert await is_circuit_breaker_open("test_source", db_path=temp_db)

        # 3. Recovery
        recovered = await record_health("test_source", "ok", strategy_used="dom_selectors", db_path=temp_db)
        assert recovered.consecutive_failures == 0
        assert not await is_circuit_breaker_open("test_source", db_path=temp_db)
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_query_adapters():
    # B2B query rewriting
    queries = ["black oversized t-shirt for men"]
    b2b_qs = adapt_queries_for_b2b(queries)
    assert len(b2b_qs) == 3
    assert any("manufacturer" in q for q in b2b_qs)
    assert any("wholesale" in q for q in b2b_qs)
    assert any("bulk" in q for q in b2b_qs)

    # Quick commerce shortening
    qc_qs = adapt_queries_for_quickcommerce(["premium heavy cotton black oversized t-shirt"])
    assert len(qc_qs) >= 1
    assert len(qc_qs[0].split()) <= 3

    # Signals expansion
    sig_qs = adapt_queries_for_signals(["oversized tee"])
    assert len(sig_qs) >= 4
    assert any("outfit" in q or "streetwear" in q for q in sig_qs)


def test_dom_parsing_b2b():
    html = """
    <html>
      <body>
        <div class="product-card">
          <h2 class="title">Wholesale Cotton Blank T-Shirts</h2>
          <span class="price">₹120 / piece</span>
          <span class="supplier-name">Apex Garments Tirupur</span>
          <span class="location">Tirupur, Tamil Nadu</span>
          <span class="moq">MOQ: 100 pcs</span>
          <span class="verified">Verified Supplier</span>
          <a class="product-link" href="https://example.com/product/123">View Details</a>
        </div>
      </body>
    </html>
    """
    spec = SourceSpec(
        id="test_b2b",
        label="Test B2B",
        group="B2B",
        kind="b2b",
        hosts=["example.com"],
        selectors={
            "container": ".product-card",
            "title": ".title",
            "price": ".price",
            "supplier": ".supplier-name",
            "location": ".location",
            "moq": ".moq",
            "url": ".product-link",
        },
    )
    items = parse_dom(html, spec=spec)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Wholesale Cotton Blank T-Shirts"
    assert item.price == 120.0
    assert item.b2b is not None
    assert item.b2b.supplier == "Apex Garments Tirupur"
    assert item.b2b.moq == "MOQ: 100 pcs"


def test_embedded_json_parsing():
    html = """
    <html>
      <head>
        <script>
          window.__myntraState = {
            "searchData": {
              "results": {
                "products": [
                  {
                    "productId": 9988,
                    "productName": "Men Black Oversized Fit T-shirt",
                    "brand": "Roadster",
                    "price": 499,
                    "mrp": 999,
                    "rating": 4.2,
                    "ratingCount": 1250,
                    "landingPageUrl": "tshirts/roadster/9988/buy"
                  }
                ]
              }
            }
          };
        </script>
      </head>
      <body></body>
    </html>
    """
    items = extract_embedded_json(html, "myntra")
    assert len(items) == 1
    assert items[0].title == "Men Black Oversized Fit T-shirt"
    assert items[0].brand == "Roadster"
    assert items[0].price == 499.0
    assert items[0].mrp == 999.0
    assert items[0].rating == 4.2
