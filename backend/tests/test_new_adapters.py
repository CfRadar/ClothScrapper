import os
import pytest
from pathlib import Path

from backend.app.scrapers.adapters import (
    get_adapter,
    AjioAdapter,
    MeeshoAdapter,
    SnapmintAdapter,
    IndiamartAdapter,
    ExportersIndiaAdapter,
    AlibabaAdapter,
    BlinkitAdapter,
    SwiggyInstamartAdapter,
    ZeptoAdapter,
    ToingAdapter,
    GoogleSignalsAdapter,
    PinterestAdapter,
    FacebookAdLibraryAdapter,
    GenericCustomAdapter,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_meesho_parser():
    fixture_path = FIXTURE_DIR / "meesho_search.html"
    assert fixture_path.exists()
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = MeeshoAdapter()
    items = adapter.parse(html)
    assert len(items) == 2
    assert "Trendy Men Black Oversized Cotton T-Shirt" in items[0].title
    assert items[0].price == 299.0
    assert items[0].rating == 4.2
    assert items[0].brand is None


def test_ajio_parser():
    fixture_path = FIXTURE_DIR / "ajio_search.html"
    assert fixture_path.exists()
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = AjioAdapter()
    items = adapter.parse(html)
    assert len(items) == 2
    assert "DNMX" in items[0].title
    assert items[0].price == 349.0
    assert "Netplay" in items[1].title
    assert items[1].price == 499.0


@pytest.mark.asyncio
async def test_snapmint_unavailable():
    adapter = SnapmintAdapter()
    res = await adapter.search("black t-shirt")
    assert res.status == "unavailable"
    assert "EMI payment platform" in (res.note or "")


def test_indiamart_parser():
    fixture_path = FIXTURE_DIR / "indiamart_search.html"
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = IndiamartAdapter()
    items = adapter.parse(html)
    assert len(items) == 2
    item1 = items[0]
    assert "Cotton Plain T-Shirt" in item1.title
    assert item1.price == 140.0
    assert item1.b2b is not None
    assert item1.b2b.supplier == "Tirupur Knits & Garments"
    assert "Tirupur" in (item1.b2b.location or "")
    assert "100" in (item1.b2b.moq or "")
    assert item1.b2b.verified is True


def test_exportersindia_parser():
    fixture_path = FIXTURE_DIR / "exportersindia_search.html"
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = ExportersIndiaAdapter()
    items = adapter.parse(html)
    assert len(items) == 1
    item = items[0]
    assert "Heavy Cotton T-Shirts" in item.title
    assert item.price == 185.0
    assert item.b2b is not None
    assert item.b2b.supplier == "Surat Apparel Hub"
    assert "Surat" in (item.b2b.location or "")


def test_alibaba_parser():
    fixture_path = FIXTURE_DIR / "alibaba_search.html"
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = AlibabaAdapter()
    items = adapter.parse(html)
    assert len(items) == 1
    item = items[0]
    assert "Custom Heavyweight Vintage" in item.title
    assert item.b2b is not None
    assert item.b2b.supplier == "Guangzhou Fashion Garments Co., Ltd."
    assert item.b2b.moq == "50 pieces"


@pytest.mark.asyncio
async def test_quick_commerce_pincode_requirement():
    # Without valid DELIVERY_PINCODE, must return needs_location
    os.environ["DELIVERY_PINCODE"] = ""
    blinkit = BlinkitAdapter()
    res = await blinkit.search("tshirt")
    assert res.status == "needs_location"

    swiggy = SwiggyInstamartAdapter()
    res2 = await swiggy.search("tshirt")
    assert res2.status == "needs_location"

    zepto = ZeptoAdapter()
    res3 = await zepto.search("tshirt")
    assert res3.status == "needs_location"


@pytest.mark.asyncio
async def test_toing_unavailable():
    toing = ToingAdapter()
    res = await toing.search("tshirt")
    assert res.status == "unavailable"
    assert "food delivery" in (res.note or "").lower()


def test_pinterest_signals_parser():
    fixture_path = FIXTURE_DIR / "pinterest_search.html"
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = PinterestAdapter()
    signals = adapter.parse(html)
    assert len(signals) >= 2
    phrases = [s.phrase for s in signals]
    assert any("streetwear" in p for p in phrases)
    assert any("graphic" in p or "lookbook" in p for p in phrases)


def test_facebook_signals_parser():
    fixture_path = FIXTURE_DIR / "facebook_search.html"
    with open(fixture_path, encoding="utf-8") as f:
        html = f.read()

    adapter = FacebookAdLibraryAdapter()
    signals = adapter.parse(html)
    assert len(signals) >= 2
    phrases = [s.phrase for s in signals]
    assert any("cotton" in p or "french terry" in p or "oversized" in p for p in phrases)


@pytest.mark.asyncio
async def test_estay_generic_custom_source():
    estay = GenericCustomAdapter("estay")
    res = await estay.search("tshirt")
    # Estay is unconfigured by default, so it returns unavailable
    assert res.status == "unavailable"
    assert "disabled" in (res.note or "").lower()


def test_dynamic_get_adapter():
    # Verify that get_adapter instantiates any declared source
    for sid in ["amazon", "myntra", "flipkart", "ajio", "indiamart", "google", "toing", "estay"]:
        ad = get_adapter(sid)
        assert ad.id == sid

    # Verify that an undeclared source falls back cleanly to GenericCustomAdapter
    dummy = get_adapter("my_future_marketplace")
    assert dummy.id == "my_future_marketplace"
