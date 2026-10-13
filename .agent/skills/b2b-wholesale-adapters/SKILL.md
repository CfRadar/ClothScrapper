---
name: b2b-wholesale-adapters
description: Architecture, deterministic query rewriting, and scraping playbooks for B2B wholesale platforms including IndiaMART, ExportersIndia, and Alibaba. Trigger when integrating B2B supplier sources or analyzing manufacturing signals.
---

# B2B Wholesale Adapters

## Purpose
Governs the integration of wholesale manufacturing and supplier directories (IndiaMART, ExportersIndia, Alibaba). B2B listings provide crucial keyword signals (fabric weight in GSM, biowash treatments, manufacturing jargon, regional production hubs like Tirupur and Ludhiana) distinct from consumer retail listings.

---

## When to Use
- Adding or maintaining B2B wholesale sources in the "B2B and wholesale" canvas group.
- Transforming retail consumer queries into high-yield supplier queries without LLM overhead.
- Extracting wholesale metrics (MOQ, verified supplier status, unit price brackets).

---

## The B2B Keyword Model

Consumer searches focus on styling ("stylish oversized black tee for college boys"), whereas wholesale supplier directories index listings around **technical fabric specifications, minimum order quantities (MOQ), and manufacturing capabilities**:
- **Manufacturing terms**: `manufacturer`, `wholesale supplier`, `bulk exporter`, `job work`, `factory price`.
- **Material specs**: `240 gsm pure cotton`, `single jersey`, `biowash`, `loopknit`, `french terry`, `silicon wash`.
- **Customization**: `private label`, `custom screen print`, `dtf puff print`, `OEM apparel`.
- **Hub references**: `Tirupur exporter`, `Ludhiana mill`.

### Deterministic Query Rewriter (Zero LLM Calls)

Use pure Python to adapt consumer brief queries into wholesale supplier searches:

```python
import re

B2B_STOPWORDS = {"stylish", "trendy", "best", "cheap", "buy", "online", "men", "women", "unisex", "college"}
DEFAULT_B2B_SUFFIX = "manufacturer wholesale"

def rewrite_to_b2b_query(consumer_query: str, fabric: str = "", gsm: str = "") -> str:
    """
    Rewrites a consumer search phrase into a high-intent wholesale B2B query in pure code.
    Example:
        'vintage black oversized graphic tee' -> 'oversized graphic tee 240 gsm wholesale manufacturer'
    """
    tokens = [t.lower() for t in re.findall(r"\b[a-z0-9]+\b", consumer_query) if t.lower() not in B2B_STOPWORDS]
    
    # Preserve core product words
    core = " ".join(tokens[:4])
    
    # Inject technical attributes if present
    spec_parts = []
    if gsm:
        spec_parts.append(f"{gsm} gsm" if "gsm" not in gsm.lower() else gsm)
    if fabric and "cotton" in fabric.lower():
        spec_parts.append("cotton")
        
    specs = " ".join(spec_parts)
    return f"{core} {specs} {DEFAULT_B2B_SUFFIX}".strip()
```

---

## Normalized B2B Item Model

B2B listings populate the standard `Item` object with an extended `b2b` dictionary:

```python
class Item(BaseModel):
    title: str
    brand: str = ""
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int = 0
    sponsored: bool = False
    url: str = ""
    source_id: str
    b2b: dict[str, Any] | None = None  # {supplier, location, moq, unit, price_range}
```

---

## Platform Playbooks

### 1. IndiaMART (`indiamart`)
- **Search URL Discovery**:
  Use the public directory search endpoint:
  `https://dir.indiamart.com/search.mp?ss={query}`
- **Card Container**: `div.mscr, div.card, div.listing-card`
- **Field Selectors**:
  - Title: `a.cardlinks, h3.title, span.title`
  - Supplier: `div.comp-name, a.company-name, span.pname`
  - Location: `span.city, div.comp-city, span.loc`
  - Price: `span.price, p.prc` (e.g. `₹ 180 / Piece`)
  - MOQ: `span.moq, span:has-text('MOQ'), span:has-text('Minimum Order Quantity')`
  - Verified Status: `span.trustseal, span:has-text('Verified Supplier')`
- **Resource Blocking**: Keep `block_images: false` if IndiaMART's lazy-loading script fails to trigger layout without stylesheets.

---

### 2. ExportersIndia (`exportersindia`)
- **Search URL**:
  `https://www.exportersindia.com/search.php?srch_catg_ty=P&term={query}`
- **Field Selectors**:
  - Card: `div.card, div.content-box`
  - Title: `h2.title a, h3 a`
  - Supplier: `p.company_name a`
  - Location: `span.location`
  - Price & MOQ: `p.price_range`

---

### 3. Alibaba (`alibaba`)
- **Warning**: Alibaba employs extreme Cloudflare and custom bot protection (Securimage / slider verification screens).
- **Rule**:
  - Treat **any** slider, puzzle challenge, or verification redirect as **`status="blocked"`**.
  - **NEVER attempt automated slider drag-and-drop or bypass.**
  - In `sources.yaml`, Alibaba must remain `default_enabled: false` and `tos_risk: "high"`.
- **Search URL (when enabled)**:
  `https://www.alibaba.com/trade/search?SearchText={query}`

---

## Rules (DO / DON'T)

### DO
- Use `resources/b2b-taxonomy.json` to extract material keywords and manufacturer hubs.
- Use deterministic string manipulation in `rewrite_to_b2b_query` (zero LLM calls).
- Stop immediately if Alibaba or IndiaMART renders a robot verification screen.

### DON'T
- DO NOT query Alibaba with rapid bursts; enforce at least 4–8 second delays.
- DO NOT use consumer queries like "buy 1 piece t-shirt" on wholesale directories.
- DO NOT attempt slider puzzle solving.

---

## Checklist Before Finishing
- [ ] B2B query rewriter tested deterministically in pure Python.
- [ ] IndiaMART and ExportersIndia selectors verified against real HTML fixtures.
- [ ] Alibaba set to `default_enabled: false` and `tos_risk: "high"`.
- [ ] Extracted items include `b2b` metadata (supplier, location, MOQ).
