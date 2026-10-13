"""
Query adaptation module for different source kinds.
Pure Python, deterministic, no LLM calls.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("backend.scrapers.query_adapters")

# Load B2B taxonomy
TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "scoring" / "resources" / "b2b_taxonomy.json"
B2B_TAXONOMY: dict[str, Any] = {}
if TAXONOMY_PATH.exists():
    try:
        with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
            B2B_TAXONOMY = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load b2b_taxonomy.json: {e}")


def _clean_consumer_terms(query: str) -> str:
    """Strips retail/consumer fluff from search queries."""
    q = query.lower()
    # Remove phrases like 'for men', 'men', 'buy online', 'offer', etc.
    noise = [
        r"\bfor men\b",
        r"\bfor women\b",
        r"\bmen\b",
        r"\bwomen\b",
        r"\bbuy online\b",
        r"\boffer\b",
        r"\bcheap\b",
        r"\bbest\b",
    ]
    for pattern in noise:
        q = re.sub(pattern, "", q)
    return re.sub(r"\s+", " ", q).strip()


def adapt_queries_for_b2b(queries: list[str]) -> list[str]:
    """
    Rewrites consumer queries to wholesale phrasing:
    e.g. '{clean_type} manufacturer', '{clean_type} wholesale', 'bulk {clean_type}'.
    Max 3 queries.
    """
    if not queries:
        return ["t shirt manufacturer", "bulk t shirt wholesale", "cotton t shirt factory"]

    base = _clean_consumer_terms(queries[0])
    if not base:
        base = "t shirt"

    # Avoid duplicating "t shirt" if already in base
    if "t-shirt" not in base and "tshirt" not in base and "t shirt" not in base:
        base = f"{base} t shirt"

    b2b_queries = [
        f"{base} manufacturer",
        f"{base} wholesale",
        f"bulk {base}",
    ]
    return b2b_queries[:3]


def adapt_queries_for_quickcommerce(queries: list[str]) -> list[str]:
    """
    Shortens queries to concise 2-3 word product terms.
    Max 2 queries.
    """
    if not queries:
        return ["black tshirt", "plain tshirt"]

    shortened: list[str] = []
    for q in queries:
        words = q.split()
        if len(words) > 3:
            # Keep first 3 salient words
            short = " ".join(words[:3])
        else:
            short = q
        clean = short.strip().lower()
        if clean and clean not in shortened:
            shortened.append(clean)
        if len(shortened) >= 2:
            break

    return shortened if shortened else ["tshirt", "men tshirt"]


def adapt_queries_for_signals(queries: list[str]) -> list[str]:
    """
    Produces seed queries plus common trend modifiers for social and search listening.
    Max 8 queries.
    """
    if not queries:
        return ["oversized t-shirt", "graphic tee styling"]

    seed = queries[0].lower().strip()
    expansions = [
        seed,
        f"{seed} outfit",
        f"{seed} aesthetic",
        f"{seed} streetwear",
        f"how to style {seed}",
        f"best {seed}",
        f"{seed} trend",
        f"{seed} drip",
    ]
    return expansions[:8]


def adapt_queries(queries: list[str], kind: str) -> list[str]:
    """
    Routes queries to the appropriate kind adapter.
    """
    if kind == "b2b":
        return adapt_queries_for_b2b(queries)
    elif kind == "quickcommerce":
        return adapt_queries_for_quickcommerce(queries)
    elif kind in ("search", "social"):
        return adapt_queries_for_signals(queries)
    else:
        # Default marketplace queries
        return queries[:5]
