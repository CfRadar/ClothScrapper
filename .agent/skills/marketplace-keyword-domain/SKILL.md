---
name: marketplace-keyword-domain
description: Provides domain knowledge, attribute taxonomy, platform SEO playbooks, and negative/stopword filtering for T-shirt keyword research across Amazon.in, Myntra, and Flipkart. Trigger when normalizing T-shirt attributes, generating marketplace queries, or formatting keywords per platform.
---

# Marketplace Keyword Domain

## Purpose
This skill encapsulates domain-specific e-commerce search engine optimization (SEO) and catalog taxonomy rules for T-shirts on India's top retail platforms: Amazon.in, Myntra, and Flipkart. It standardizes T-shirt attributes, documents platform-specific indexing and ranking behaviors, and provides stopword/noise filter lists to ensure only high-converting, compliant shopper keywords are extracted.

## When to use
- When the AI Planner interprets seller input briefs into structured attributes (neck, fit, sleeve, fabric, theme).
- When generating seed search queries for marketplace scrapers.
- When cleaning scraped product titles, autosuggest completions, and related searches.
- When formatting keyword recommendations tailored to platform-specific constraints (Amazon backend search terms vs. Myntra attribute filters vs. Flipkart search tags).
- When identifying trademarked or branded terms that must be flagged rather than recommended.

## Step-by-step procedure

1. **Extract and Map Attributes from Seller Brief**:
   - Compare the raw seller brief against `resources/tshirt-attribute-taxonomy.json`.
   - Identify core attributes: `fit` (e.g., oversized, slim, regular), `neck` (e.g., round neck, polo, henley), `sleeve` (e.g., half sleeve, full sleeve, drop shoulder), `fabric` (e.g., 100% cotton, French terry, dry-fit), `pattern` (e.g., graphic print, solid, acid wash), and `target_audience` (e.g., men, women, unisex).
   - Normalize regional phrasing (e.g., "banyan cloth" -> "100% cotton", "loose fit" -> "oversized / boxy fit").

2. **Formulate Target Market Queries**:
   - Combine normalized attributes into high-intent search queries based on platform search habits in `resources/platform-playbooks.md`.
   - Example Amazon: `oversized t shirt for men cotton`
   - Example Flipkart: `men oversized round neck t-shirt black`
   - Example Myntra: `men-oversized-cotton-tshirt`

3. **Apply Platform-Specific Keyword Constraints**:
   - **Amazon.in**:
     - Extract short-tail and long-tail shopper search phrases.
     - Isolate non-redundant backend search terms (check and adhere to the Amazon 249-byte limit, excluding punctuation).
     - Prioritize keyword density for Title (`Brand + Attributes + Material + Use case`) and 5 Bullet points.
   - **Myntra**:
     - Emphasize structured attribute tag matches (neck, sleeve, fit, occasion) because Myntra search operates heavily as a faceted filter system.
     - Provide style-driven and aesthetic keywords (e.g., `streetwear`, `minimalist`, `college wear`).
   - **Flipkart**:
     - Optimize for the standard Flipkart discovery formula: `Brand + Type + Fit + Color + Size/Pack + Key feature`.
     - Generate high-volume Hindi-English transliterated query matches (e.g., `suti t shirt`, `printed t shirt boys`).

4. **Filter Noise and Stopwords**:
   - Load `resources/stopwords.txt`.
   - Strip generic transaction stopwords (`buy`, `online`, `shopping`, `best price`, `cheap`, `offer`) from final keyword tags unless specifically relevant to search intent.
   - Separate volume indicators (e.g., `combo offer`, `pack of 2`) into structural attributes rather than organic search keywords.

5. **Scan and Flag Trademark / Brand Violations**:
   - Cross-check candidate keywords against popular proprietary brands (e.g., Nike, Adidas, Marvel, Disney, Anime names like Naruto/Goku, celebrities).
   - If a brief mentions "Marvel style", recommend descriptive keywords (e.g., `superhero graphic t shirt`, `comic printed tee`) and explicitly flag the brand name as a trademark violation risk.

## Rules (do / don't)
- **DO** verify current Amazon backend search term byte limits before indexing suggestions (typically 249 bytes in bytes, not character count).
- **DO** preserve Indian cultural color descriptors (e.g., `pista green`, `rani pink`, `haldi yellow`, `mehendi green`) when present in the brief, as Indian shoppers frequently search these exact terms.
- **DO** keep keywords clean and singular/plural normalized without duplicate stems.
- **DON'T** ever recommend trademarked brand names (e.g., "Zara fit", "Levi's style", "Marvel tee") as seller keywords. Flag them into the "Other factors" section as legal/intellectual property risks.
- **DON'T** suggest spammy keyword-stuffing patterns (e.g., repeating `tshirt t-shirt tee t shirt`).
- **DON'T** pollute the keyword list with platform metrics, price points, or search volume scores. Output pure keyword strings only.

## Examples

### Example 1: Seller Brief Parsing
- **Input Brief**: "Black oversized heavy cotton drop-shoulder tee for college guys with minimal Japanese graphic on back"
- **Mapped Taxonomy**:
  - `type`: graphic, oversized, drop shoulder
  - `neck`: round neck
  - `sleeve`: half sleeve / drop shoulder
  - `fabric`: 240+ GSM heavy cotton
  - `color`: black
  - `gender`: men / unisex
  - `occasion`: casual / college / streetwear
  - `pattern`: back print, minimal Japanese graphic

### Example 2: Platform-Tailored Keyword Output
- **Amazon.in**:
  - `oversized t shirt for men`
  - `drop shoulder t shirt men`
  - `heavyweight cotton t shirt 240 gsm`
  - `back printed graphic t shirt`
  - `japanese aesthetic streetwear tee`
- **Myntra**:
  - `men black oversized round neck t shirt`
  - `loose fit cotton streetwear t shirt`
  - `back print graphic casual tee`
  - `drop shoulder cotton t shirt`
- **Flipkart**:
  - `men printed round neck pure cotton black t-shirt`
  - `oversized drop shoulder t shirt for boys`
  - `loose fit black graphic t shirt`
  - `college wear casual t shirt`

## Checklist before finishing
- [ ] Attributes verified against `resources/tshirt-attribute-taxonomy.json`.
- [ ] Platform playbooks consulted for naming formulas and backend limits.
- [ ] `resources/stopwords.txt` applied to eliminate junk terms.
- [ ] All trademark/IP terms filtered out or tagged for the "Other factors" alert section.
- [ ] Output list formatted cleanly as plain keyword strings per platform.
