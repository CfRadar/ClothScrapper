---
name: keyword-scoring-engine
description: Executes deterministic keyword extraction and scoring in pure Python using a multi-factor mathematical formula. Use when generating, ranking, and deduplicating n-gram candidate keywords from marketplace scrapes and social signals before sending the top 60 to the AI Analyst.
---

# Keyword Scoring Engine

## Purpose
This skill executes the core quantitative ranking of search keyword candidates using pure Python algorithms rather than expensive LLM tokens. It extracts 1-to-4 word n-grams from scraped titles, autosuggest completions, related searches, and social listening phrases, applies a multi-factor mathematical scoring formula with min-max normalization, and outputs the top ~60 highest-intent keywords per platform for final AI Analyst curation.

## When to use
- Between the data scraping stage and the AI Analyst agent stage.
- When generating candidate n-grams from raw titles, suggestions, and social posts.
- When filtering stopwords, pure numbers, and noise words.
- When ranking keyword relevance deterministically to conserve the OpenRouter free LLM budget.
- When running unit tests on keyword extraction and normalization math.

## Step-by-step procedure

1. **Generate Raw Candidate N-Grams (1-4 words)**:
   - Tokenize text from:
     - Scraped product titles across all returned items.
     - Platform autosuggest strings and related search chips.
     - Social listener phrases and community post titles.
   - Strip punctuation, lowercase all tokens, and eliminate pure numbers.
   - Filter out stopwords from `marketplace-keyword-domain/resources/stopwords.txt`.
   - Extract contiguous spans of length $N \in [1, 4]$. Drop any n-gram that begins or ends with a stopword.

2. **Deduplicate and Stem Plurals**:
   - Normalize simple plurals (e.g. `oversized t-shirts` -> `oversized t-shirt`, `cotton tees` -> `cotton tee`).
   - Retain unique canonical candidate strings in a candidate set per platform.

3. **Calculate Raw Feature Components**:
   For each candidate keyword $k$:
   - **`suggest_presence`**: Binary indicator ($1.0$ if $k$ appears inside any autosuggest or related search query, else $0.0$).
   - **`title_freq_top10`**: Count of occurrences of $k$ across the top 10 ranked product listing titles.
   - **`rank_weighted_reviews`**: Sum over all products containing $k$ of:
     $$\text{Weight}(p) = \frac{1}{\sqrt{\text{position}(p)}} \times \ln(1 + \text{reviews}(p))$$
   - **`social_mentions`**: Aggregate mention frequency from Reddit fashion posts and wish-phrases.
   - **`attribute_match_to_brief`**: Count of matching attributes between $k$ and the seller's input brief (fit, neck, sleeve, fabric, theme).

4. **Min-Max Normalize Components**:
   - For each metric $M \in \{\text{suggest}, \text{title}, \text{reviews}, \text{social}, \text{attr}\}$:
     $$M_{\text{norm}}(k) = \frac{M(k) - \min(M)}{\max(M) - \min(M)}$$
     *(If $\max(M) == \min(M)$, normalize to $1.0$ if $\max(M) > 0$ else $0.0$).*

5. **Compute Deterministic Composite Score**:
   Apply the project standard weighting formula:
   $$\text{Score}(k) = 0.35 \times \text{suggest}_{\text{norm}} + 0.25 \times \text{title}_{\text{norm}} + 0.20 \times \text{reviews}_{\text{norm}} + 0.10 \times \text{social}_{\text{norm}} + 0.10 \times \text{attr}_{\text{norm}}$$

6. **Filter Top ~60 Candidates per Platform**:
   - Sort descending by $\text{Score}(k)$.
   - Slice the top 60 candidate keywords.
   - Hand off clean list to the AI Analyst agent for final semantic polish and trademark screening.

## Rules (do / don't)
- **DO** perform all candidate extraction, n-gram generation, and mathematical scoring deterministically in Python.
- **DO** normalize all scoring components on a per-platform basis.
- **DO** drop pure digits (e.g. `100`, `2024`, `500`) unless part of an attribute like `240 gsm`.
- **DON'T** call the LLM to score or rank candidates. The LLM's only job is final semantic selection and grouping.
- **DON'T** expose raw numeric scores or percentages in the final user-facing keyword cards.
- **DON'T** allow duplicate plurals or near-identical stems into the top candidate pool.

## Examples

### Unit-Test Template with Tiny Fixture
Save as `tests/test_keyword_scoring.py`:
```python
import pytest
from backend.services.scoring import score_platform_candidates

SAMPLE_FIXTURE = {
    "products": [
        {"title": "Men Oversized Pure Cotton T-Shirt Drop Shoulder", "position": 1, "rating_count": 1200},
        {"title": "Oversized Loose Fit Cotton T-Shirt", "position": 2, "rating_count": 850},
        {"title": "Regular Fit Casual Tee", "position": 3, "rating_count": 50},
    ],
    "suggestions": ["oversized cotton t shirt", "drop shoulder t shirt"],
    "related_searches": ["baggy fit t shirt for men"],
    "social_signals": [{"phrase": "looking for oversized cotton tee", "mentions": 4}],
    "brief_attributes": ["oversized", "cotton", "drop shoulder"]
}

def test_scoring_weights_and_ranking():
    scored = score_platform_candidates(
        products=SAMPLE_FIXTURE["products"],
        suggestions=SAMPLE_FIXTURE["suggestions"],
        related_searches=SAMPLE_FIXTURE["related_searches"],
        social_signals=SAMPLE_FIXTURE["social_signals"],
        brief_attributes=SAMPLE_FIXTURE["brief_attributes"],
        top_n=10
    )
    
    assert len(scored) > 0
    top_keyword = scored[0]["keyword"]
    # High-intent phrase present in suggestions and titles should rank top
    assert "oversized" in top_keyword or "cotton" in top_keyword
    assert 0.0 <= scored[0]["score"] <= 1.0
```

## Checklist before finishing
- [ ] Formula matches: $0.35*\text{suggest} + 0.25*\text{title} + 0.20*\text{reviews} + 0.10*\text{social} + 0.10*\text{attr}$.
- [ ] Min-max normalization handled safely without division-by-zero.
- [ ] Stopwords and numbers stripped from n-grams.
- [ ] Plurals deduped.
- [ ] Python script `scripts/score_keywords.py` executable with `--input` JSON file.
- [ ] Unit tests pass against sample fixture.
