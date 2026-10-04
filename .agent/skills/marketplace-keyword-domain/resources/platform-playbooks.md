# E-Commerce Platform Playbooks: T-Shirt SEO (India)

This document provides platform-specific search behaviors, catalog naming schemas, backend keyword fields, and indexing rules for Amazon.in, Myntra, and Flipkart.

---

## 1. Amazon.in

### Catalog Structure & Title Convention
- **Recommended Title Formula**:
  `[Brand] + [Gender/Target] + [Fit] + [Neck/Style] + [Pattern/Feature] + [T-Shirt] + (Pack of X / Material)`
- **Example**: `UrbanCraft Men's Oversized Cotton Drop Shoulder Graphic Back Printed T-Shirt`
- **Title Character Limit**: Max 200 characters (including spaces). Amazon suppresses listings with titles over 200 characters or containing promotional phrases ("Free shipping", "Best seller").
- **Bullet Points (Key Product Features)**:
  - 5 bullet points, max 150-200 characters each.
  - Natural keyword placement: Material quality (e.g., 220 GSM 100% combed cotton), Fit description, Styling advice, Wash care, Occasion suitability.

### Backend Search Terms (Generic Keywords)
- **Field Limit**: **249 bytes** (IMPORTANT: bytes, not characters; UTF-8 multi-byte characters consume 2-4 bytes each). Always tell the agent to verify current Seller Central limits.
- **Rules**:
  - Do NOT include commas, semicolons, or punctuation (use single space as delimiter).
  - Do NOT repeat words already present in the title or brand name.
  - Do NOT include competitor brand names or ASINs (violates Amazon policy and risks suspension).
  - Include common misspellings, colloquial synonyms, and secondary intent terms (e.g., `loose tee roundneck baggy drop-shoulder streetwear bts anime gym casual summer top`).

### Search Indexing Nuances
- Amazon A9/COSMO search engine matches words regardless of order.
- Plurals and singulars are handled automatically by stemmers, but irregular terms should be included.
- Autosuggest completions from `completion.amazon.in` represent high real-time search volume.

---

## 2. Myntra

### Catalog Structure & Title Convention
- Myntra is fundamentally an **attribute-driven fashion discovery platform**, not a keyword-stuffing search engine.
- Titles are often auto-composed by Myntra's catalog engine using structured attributes:
  `[Brand] + [Fit] + [Neck Type] + [Print/Pattern] + [Sleeve Type] + [Color] + T-shirt`
- **Example**: `Roadster Men Charcoal Grey Solid Drop Shoulder Cotton T-shirt`

### Attribute Taxonomy & Facets
Myntra users browse primarily through category filters (facets). Key indexing attributes:
- **Neck**: Round Neck, Polo Collar, Mandarin Collar, V-Neck, High Neck, Hooded.
- **Fit**: Oversized, Regular Fit, Slim Fit, Boxy, Relaxed Fit.
- **Sleeve Length**: Short Sleeves, Full Sleeves, Three-Quarter Sleeves, Sleeveless.
- **Pattern**: Solid, Typography, Graphic Print, Striped, Colorblocked, Tie and Dye.
- **Occasion**: Casual, Daily, Streetwear, Party, Sports.
- **Fabric**: Cotton, Pure Cotton, Cotton Blend, Polyester, French Terry, Waffle.
- **Brand Tags & Themes**: Aesthetic lifestyle tags (e.g., Y2K, Grunge, Korean Fashion, Minimalist).

### Keyword Usage Difference
- Avoid repetitive generic keywords.
- Keywords must directly map to high-ranking filter attributes and trending visual curation tags.
- Myntra's search places high weight on brand affinity, catalog completeness score, and discount depth.

---

## 3. Flipkart

### Catalog Structure & Title Convention
- **Flipkart Title Formula**:
  `[Brand] + [Type] + [Fit] + [Color] + [Size / Pack Indicator] + [Key Feature / Material] + T-Shirt`
- **Example**: `TripCity Men Oversized Fit Black Solid Pure Cotton Round Neck T-Shirt (Pack of 1)`
- Maximum character limit: 120-150 characters.

### Search Tags & Catalog Attributes
- Flipkart uses explicit "Search Keywords / Search Tags" in seller listings (up to 20-30 comma-separated phrases).
- Flipkart shoppers frequently use vernacular transliteration (Hinglish):
  - `suti t shirt` (pure cotton t-shirt)
  - `kali t shirt` (black t-shirt)
  - `ladko ki t shirt` (boys t-shirt)
  - `dheeli t shirt` (loose/oversized t-shirt)
- Key features must be clear: Pocket, Anti-odor, Breathable, Bio-washed.

### Keyword Usage Difference
- Value-conscious queries are prominent: `combo t shirts`, `cotton t shirt under 300`, `loose t shirt for daily wear`.
- Flipkart search algorithm rewards exact phrase matches in titles and explicit search tags.

---

## Comparative Keyword Strategy Matrix

| Dimension | Amazon.in | Myntra | Flipkart |
|---|---|---|---|
| **Primary Driver** | Keyword match + Sales velocity + Search term bytes | Attribute facets + Brand aesthetics + Curated tags | Title keyword formula + Price point + Transliterations |
| **Backend Fields** | Single search terms field (<=249 bytes) | Attribute metadata fields + Style tags | Search Keywords field (tags) |
| **User Phrasing** | High-intent English specs (e.g. `240 gsm cotton oversized t shirt`) | Trend/Style queries (e.g. `streetwear baggy fit tee`) | Value & Hinglish queries (e.g. `black combo t shirt boys`) |
| **Listing Focus** | 5 detailed feature bullets + A+ content keywords | High quality lookbook images + Exact filter compliance | Accurate Title formula + Bulleted attributes |
