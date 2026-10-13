---
name: quick-commerce-adapters
description: Technical playbooks, pincode injection workflows, and catalog rules for Indian quick commerce platforms including Blinkit, Swiggy Instamart, Zepto, and the Toing stub. Trigger when configuring or auditing quick-commerce adapters.
---

# Quick Commerce Adapters

## Purpose
Governs the integration of 10-to-20-minute hyper-local delivery apps (Blinkit, Swiggy Instamart, Zepto). Provides realistic relevance guidelines, geolocation/pincode handling routines, and rules for handling food-only apps like Toing.

---

## When to Use
- Managing adapters in the "Quick commerce" canvas group.
- Injecting delivery pincodes into hyper-local single page applications.
- Evaluating apparel catalog availability on instant grocery networks.

---

## Honest Relevance & Scope Reality

> [!WARNING]
> Quick commerce apps in India are primarily instant delivery channels for groceries, fresh produce, and FMCG daily essentials. Apparel coverage is **very narrow**—limited almost exclusively to basic innerwear, plain undershirts, or seasonal emergency basics (e.g. plain white vests, raincoats).
>
> **Defaults**: Every quick commerce adapter must be configured with `default_enabled: false` and `relevance: "low"`.
> **Query Adaptation**: Do not send long conceptual briefs (e.g. "heavyweight graphic oversized vintage tee"). Trim to 2–3 words (e.g. "cotton t-shirt", "plain tee").

---

## Delivery Location & Pincode Flow

Quick commerce catalogs are strictly partitioned by hyper-local dark stores (micro-fulfillment centers). Without an active delivery pincode or latitude/longitude, search endpoints return either empty results or a location-blocking modal.

### Pincode Validation & Injection Routine

1. **Environment Configuration**:
   Require `DELIVERY_PINCODE` in `backend/.env`.
2. **Regex Validation**:
   Validate before initiating requests:
   ```python
   import re

   def validate_pincode(pincode: str) -> bool:
       return bool(re.match(r"^\d{6}$", pincode.strip()))
   ```
3. **Failure Classification**:
   If `DELIVERY_PINCODE` is empty or invalid, do not hang on location prompts. Return immediately:
   ```python
   return SourceResult(
       source_id=self.id,
       status="degraded",
       strategy_used="none",
       failure_cause="needs_location",
       note="Quick commerce searches require an Indian 6-digit DELIVERY_PINCODE in backend/.env."
   )
   ```

---

## Platform Playbooks

### 1. Blinkit (`blinkit`)
- **Search URL**: `https://blinkit.com/s/?q={query}`
- **Pincode Injection Flow**:
  1. Navigate to `https://blinkit.com/`.
  2. If location modal appears (`button:has-text('Detect my location')`, `input[placeholder*='search delivery location']`), click the manual input.
  3. Type the 6-digit `DELIVERY_PINCODE` and select the first dropdown suggestion.
  4. Once dark store cookie is set, proceed to search URL.
- **Card Container**: `div[data-test-id='product-card'], div.product-card`
- **Field Selectors**:
  - Title: `div.Product__UpdatedTitle, div.tw-text-sm`
  - Price: `div.Product__UpdatedPrice, span.tw-font-bold`

---

### 2. Swiggy Instamart (`instamart`)
- **Search URL**: `https://www.swiggy.com/instamart/search?custom_back=true&query={query}`
- **Location Requirement**:
  Requires setting address or pincode via Swiggy web header prompt (`span:has-text('Other'), span:has-text('Select Location')`).
- **Strategy**: Strategy 3 (Network Capture). Intercept internal API `/instamart/search` which returns JSON products array.

---

### 3. Zepto (`zepto`)
- **Search URL**: `https://www.zeptonow.com/search?q={query}`
- **Card Container**: `a[data-testid='product-card'], div[data-testid='product-card']`
- **Field Selectors**:
  - Title: `h5[data-testid='product-card-title']`
  - Price: `h4[data-testid='product-card-price']`

---

### 4. Toing Stub (`toing`)
- **Platform Reality**: Toing is Swiggy's budget food-delivery app targeted at low-ticket meals. It has **no apparel catalog** and no public web search directory.
- **Configuration Rule**:
  **Do NOT write a scraper for Toing.** Register it strictly as a status override in `sources.yaml`:
  ```yaml
  - id: toing
    label: "Toing"
    group: "quickcommerce"
    kind: "quickcommerce"
    roles: ["signal"]
    default_enabled: false
    tos_risk: "low"
    relevance: "low"
    status_override: "unavailable"
    status_reason: "Food delivery app, no apparel catalog or public web search"
    hosts:
      - "toing.com"
  ```

---

## Rules (DO / DON'T)

### DO
- Validate `DELIVERY_PINCODE` with `^\d{6}$`.
- Mark the cause as `needs_location` if no valid pincode is provided.
- Keep quick commerce queries short (2–3 words).
- Register Toing with `status_override: unavailable`.

### DON'T
- DO NOT enable quick commerce adapters by default (`default_enabled: false`).
- DO NOT fake apparel listings for food delivery apps.
- DO NOT scrape without an Indian delivery location configured.

---

## Checklist Before Finishing
- [ ] Pincode validation regex `^\d{6}$` enforced.
- [ ] Missing pincode gracefully mapped to `failure_cause: "needs_location"`.
- [ ] Toing stub registered as `unavailable` with factual reason.
- [ ] Quick commerce sources set to `relevance: "low"` and `default_enabled: false`.
