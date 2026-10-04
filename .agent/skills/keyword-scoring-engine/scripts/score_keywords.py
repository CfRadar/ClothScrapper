#!/usr/bin/env python3
"""
scripts/score_keywords.py

Usage:
    python scripts/score_keywords.py --input sample_data.json --platform amazon
    python scripts/score_keywords.py --help

Description:
    Deterministic keyword scoring engine for e-commerce search optimization.
    Extracts n-grams (1-4 words) from scraped marketplace products, autosuggest queries,
    related searches, and social listening signals.
    
    Applies the mathematical scoring formula:
      Score = 0.35 * suggest_presence
            + 0.25 * title_freq_top10
            + 0.20 * rank_weighted_reviews
            + 0.10 * social_mentions
            + 0.10 * attribute_match_to_brief

    Each feature component is min-max normalized [0.0, 1.0] across the platform candidate pool.
    Ranks candidates and outputs top ~60 clean shopper keywords for final LLM Analyst review.

Requirements:
    Standard Python 3 (json, math, re, argparse). No external dependencies.
"""

import sys
import os
import re
import json
import math
import argparse
from typing import List, Dict, Set, Any

DEFAULT_STOPWORDS = {
    "buy", "online", "best", "price", "cheap", "offer", "deals", "discount",
    "free", "shipping", "for", "with", "in", "at", "and", "or", "the", "a", "an",
    "of", "to", "from", "by", "on", "is", "this", "pack", "combo", "piece", "pcs",
    "rs", "inr", "top", "rated", "genuine", "authentic", "review", "reviews",
    "ki", "ka", "ke", "ko", "se", "mein", "par", "hai", "wale", "wali", "wala"
}

def clean_token(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower().strip())

def extract_ngrams(text: str, n_min: int = 1, n_max: int = 4, stopwords: Set[str] = None) -> List[str]:
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS
    
    # Tokenize words
    words = [clean_token(w) for w in re.split(r"[\s\-_/,\.()]+", text) if w]
    words = [w for w in words if w and not w.isdigit()] # Drop pure numbers

    ngrams = []
    length = len(words)
    for n in range(n_min, min(n_max + 1, length + 1)):
        for i in range(length - n + 1):
            chunk = words[i:i + n]
            # Discard if starts or ends with stopword
            if chunk[0] in stopwords or chunk[-1] in stopwords:
                continue
            phrase = " ".join(chunk)
            if len(phrase) >= 3:
                ngrams.append(phrase)
    return ngrams

def min_max_normalize(values: Dict[str, float]) -> Dict[str, float]:
    if not values:
        return {}
    v_min = min(values.values())
    v_max = max(values.values())
    if math.isclose(v_max, v_min):
        return {k: 1.0 if v_max > 0 else 0.0 for k in values}
    return {k: (v - v_min) / (v_max - v_min) for k, v in values.items()}

def score_platform_candidates(
    products: List[Dict[str, Any]],
    suggestions: List[str],
    related_searches: List[str],
    social_signals: List[Dict[str, Any]],
    brief_attributes: List[str],
    stopwords: Set[str] = None,
    top_n: int = 60
) -> List[Dict[str, Any]]:
    """
    Computes keyword scores using deterministic formula:
    Score = 0.35*suggest_presence + 0.25*title_freq_top10 + 0.20*rank_weighted_reviews + 0.10*social_mentions + 0.10*attribute_match
    """
    if stopwords is None:
        stopwords = DEFAULT_STOPWORDS

    raw_candidates: Set[str] = set()

    # 1. Collect n-grams from suggestions & related searches
    for s in suggestions + related_searches:
        for ng in extract_ngrams(s, 1, 4, stopwords):
            raw_candidates.add(ng)

    # 2. Collect n-grams from top product titles
    for p in products:
        title = p.get("title", "")
        for ng in extract_ngrams(title, 1, 4, stopwords):
            raw_candidates.add(ng)

    # 3. Collect from social phrases
    for sig in social_signals:
        phrase = sig.get("phrase", "")
        for ng in extract_ngrams(phrase, 1, 4, stopwords):
            raw_candidates.add(ng)

    if not raw_candidates:
        return []

    # Component raw trackers
    suggest_presence = {c: 0.0 for c in raw_candidates}
    title_freq_top10 = {c: 0.0 for c in raw_candidates}
    rank_weighted_reviews = {c: 0.0 for c in raw_candidates}
    social_mentions = {c: 0.0 for c in raw_candidates}
    attribute_match = {c: 0.0 for c in raw_candidates}

    # Set of suggestion strings for exact/substring matching
    lower_suggestions = [s.lower() for s in suggestions + related_searches]
    for c in raw_candidates:
        if any(c in s for s in lower_suggestions):
            suggest_presence[c] = 1.0

    # Top 10 product title frequency & review scores
    top_10_products = sorted(products, key=lambda x: x.get("position", 999))[:10]
    for p in top_10_products:
        p_title = p.get("title", "").lower()
        for c in raw_candidates:
            if c in p_title:
                title_freq_top10[c] += 1.0

    # Rank weighted review score across all products: (1 / position) * log(reviews + 1)
    for p in products:
        pos = max(1, p.get("position", 50))
        reviews = max(0, p.get("rating_count", 0) or 0)
        weight = (1.0 / math.sqrt(pos)) * math.log1p(reviews)
        p_title = p.get("title", "").lower()
        for c in raw_candidates:
            if c in p_title:
                rank_weighted_reviews[c] += weight

    # Social signal mentions
    for sig in social_signals:
        s_phrase = sig.get("phrase", "").lower()
        s_count = sig.get("mentions", 1)
        for c in raw_candidates:
            if c in s_phrase:
                social_mentions[c] += float(s_count)

    # Attribute match to brief
    lower_brief_attrs = [a.lower().strip() for a in brief_attributes if a]
    for c in raw_candidates:
        for attr in lower_brief_attrs:
            if attr in c or c in attr:
                attribute_match[c] += 1.0

    # Min-Max Normalization per component
    norm_suggest = min_max_normalize(suggest_presence)
    norm_title = min_max_normalize(title_freq_top10)
    norm_reviews = min_max_normalize(rank_weighted_reviews)
    norm_social = min_max_normalize(social_mentions)
    norm_attr = min_max_normalize(attribute_match)

    scored_list = []
    for c in raw_candidates:
        score = (
            0.35 * norm_suggest.get(c, 0.0) +
            0.25 * norm_title.get(c, 0.0) +
            0.20 * norm_reviews.get(c, 0.0) +
            0.10 * norm_social.get(c, 0.0) +
            0.10 * norm_attr.get(c, 0.0)
        )
        scored_list.append({
            "keyword": c,
            "score": round(score, 4),
            "suggest_presence": norm_suggest.get(c, 0.0),
            "title_freq_top10": norm_title.get(c, 0.0),
            "rank_weighted_reviews": round(norm_reviews.get(c, 0.0), 3),
            "social_mentions": norm_social.get(c, 0.0),
            "attribute_match": norm_attr.get(c, 0.0)
        })

    # Sort descending by score
    scored_list.sort(key=lambda x: x["score"], reverse=True)
    return scored_list[:top_n]

def main():
    parser = argparse.ArgumentParser(description="Deterministic Keyword Scoring CLI")
    parser.add_argument("--input", required=True, help="Path to scraped data JSON file")
    parser.add_argument("--platform", default="amazon", help="Target platform (amazon, myntra, flipkart)")
    parser.add_argument("--top", type=int, default=60, help="Number of keywords to output")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data.get("products", [])
    suggestions = data.get("suggestions", [])
    related_searches = data.get("related_searches", [])
    social_signals = data.get("social_signals", [])
    brief_attrs = data.get("brief_attributes", [])

    results = score_platform_candidates(
        products=products,
        suggestions=suggestions,
        related_searches=related_searches,
        social_signals=social_signals,
        brief_attributes=brief_attrs,
        top_n=args.top
    )

    print(f"\n[TOP {len(results)} KEYWORDS FOR {args.platform.upper()} (Deterministic Scoring)]")
    print(f"{'Rank':<5} | {'Keyword':<35} | {'Score':<8} | {'Suggest':<8} | {'Reviews':<8}")
    print("-" * 75)
    for idx, r in enumerate(results[:25], 1):
        print(f"{idx:<5} | {r['keyword']:<35} | {r['score']:<8} | {r['suggest_presence']:<8} | {r['rank_weighted_reviews']:<8}")

    print(f"\nTotal scored keywords ready for Analyst: {len(results)}")

if __name__ == "__main__":
    main()
