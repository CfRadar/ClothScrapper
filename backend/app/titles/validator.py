import json
import os
import re
from pathlib import Path
from typing import Any

from backend.app.schemas import ProductBrief, TitlePart, TitleSuggestion
from backend.app.titles.composer import compose_title

CLAIM_WORDS = {
    "cotton",
    "polyester",
    "pure",
    "premium",
    "organic",
    "dri-fit",
    "drifit",
    "stretch",
    "100%",
    "gsm",
    "silk",
    "linen",
    "spandex",
    "rayon",
    "fleece",
}

DEFAULT_PRUNE_ORDER = [
    "feature",
    "occasion",
    "pack",
    "size",
    "pattern",
    "neck",
    "sleeve",
    "fabric",
    "fit",
]


def load_taxonomy_words() -> set[str]:
    """Load canonical attribute taxonomy words from skills / resources."""
    words: set[str] = set()
    paths = [
        Path("backend/app/scoring/resources/b2b_taxonomy.json"),
        Path(".agent/skills/marketplace-keyword-domain/resources/tshirt-attribute-taxonomy.json"),
    ]
    for p in paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for v in data.values():
                            if isinstance(v, list):
                                for item in v:
                                    words.update(str(item).lower().split())
                            elif isinstance(v, dict):
                                for sub_v in v.values():
                                    if isinstance(sub_v, list):
                                        for item in sub_v:
                                            words.update(str(item).lower().split())
            except Exception:
                pass
    return words


_TAXONOMY_WORDS: set[str] | None = None


def get_taxonomy_words() -> set[str]:
    global _TAXONOMY_WORDS
    if _TAXONOMY_WORDS is None:
        _TAXONOMY_WORDS = load_taxonomy_words()
    return _TAXONOMY_WORDS


def extract_brief_words(brief: ProductBrief) -> set[str]:
    """Extract all individual normalized words present in the brief."""
    text_chunks = [
        brief.tshirt_type,
        brief.color,
        brief.gender,
        brief.fit or "",
        brief.fabric or "",
        brief.neck or "",
        brief.sleeve or "",
        brief.print_or_design or "",
        brief.occasion or "",
        brief.brand_name or "",
        brief.pack or "",
        brief.sizes or "",
        brief.extra_details or "",
    ]
    full_text = " ".join(text_chunks).lower()
    return set(re.findall(r"[a-z0-9%+-]+", full_text))


def validate_and_compose_title(
    raw_parts: list[TitlePart],
    style: str,
    platform: str,
    brief: ProductBrief,
    platform_keywords: list[str],
    rules: dict[str, Any],
) -> TitleSuggestion:
    """
    Validates title parts against vocabulary, unsupported claims, forbidden words,
    and brand rules. Composes the title in code and prunes length down to hard limits.
    """
    plat_rule = rules.get("platforms", {}).get(platform, {})
    recommended_max = plat_rule.get("recommended_max", 150)
    hard_max = plat_rule.get("hard_max", 200)
    forbidden_patterns = plat_rule.get("forbidden_patterns", [])
    global_forbidden = rules.get("global_forbidden_patterns", [])
    prune_order = rules.get("prune_priority_order", DEFAULT_PRUNE_ORDER)

    warnings: list[str] = []
    brief_words = extract_brief_words(brief)

    # Allowed vocabulary = brief words ∪ platform keywords words ∪ taxonomy words
    kw_words: set[str] = set()
    for kw in platform_keywords:
        kw_words.update(re.findall(r"\b[a-z0-9%+-]+\b", kw.lower()))

    taxonomy_words = get_taxonomy_words()
    allowed_vocabulary = brief_words | kw_words | taxonomy_words

    validated_parts: list[TitlePart] = []

    for part in raw_parts:
        text = part.text.strip()
        if not text:
            continue

        label = part.label

        # (c) Brand check: brand part is allowed ONLY if brand_name was provided in brief
        if label == "brand":
            if not brief.brand_name or not brief.brand_name.strip():
                warnings.append(f"Removed unprovided brand: {text}")
                continue

        # (d) Forbidden pattern check
        has_forbidden = False
        for pat in forbidden_patterns + global_forbidden:
            # Case sensitive only for uppercase word pattern
            flags = 0 if "[A-Z]" in pat else re.IGNORECASE
            if re.search(pat, text, flags):
                has_forbidden = True
                warnings.append(f"Removed forbidden pattern: {text}")
                break
        if has_forbidden:
            continue

        # (b) Unsupported claim check: material or quality claims allowed only if in brief
        part_tokens = set(re.findall(r"[a-z0-9%+-]+", text.lower()))
        unsupported = False
        for tok in part_tokens:
            if tok in CLAIM_WORDS or re.match(r"^\d+gsm$", tok):
                if tok not in brief_words:
                    unsupported = True
                    warnings.append(f"Removed unsupported claim '{tok}' in part: {text}")
                    break
        if unsupported:
            continue

        # (a) Vocabulary check: words must be in allowed vocabulary
        connectors = {
            "and", "for", "with", "of", "in", "the", "a", "an", "pack", "men", "women",
            "kids", "unisex", "tee", "tshirt", "t-shirt", "shirt", "top", "combo",
        }
        unknown_tokens = [
            t for t in part_tokens
            if t not in allowed_vocabulary and t not in connectors and not t.isdigit()
        ]
        if unknown_tokens:
            warnings.append(f"Removed unrecognized word '{unknown_tokens[0]}' in part: {text}")
            continue

        validated_parts.append(TitlePart(label=label, text=text))

    # Compose title initially
    composed_text, active_parts = compose_title(validated_parts, platform, rules)

    # (f) Length pruning: if text exceeds hard_max, drop lowest priority parts
    if len(composed_text) > hard_max:
        for drop_label in prune_order:
            if len(composed_text) <= hard_max:
                break
            # Filter out part with drop_label
            filtered = [p for p in active_parts if p.label != drop_label]
            if len(filtered) < len(active_parts):
                active_parts = filtered
                composed_text, active_parts = compose_title(active_parts, platform, rules)
                warnings.append(f"Trimmed '{drop_label}' to satisfy hard length limit of {hard_max}")

    # Check recommended length
    if len(composed_text) > recommended_max:
        warnings.append(f"Title length ({len(composed_text)}) exceeds recommended maximum of {recommended_max}")

    return TitleSuggestion(
        style=style,  # type: ignore[arg-type]
        parts=active_parts,
        text=composed_text,
        title=composed_text,
        length=len(composed_text),
        recommended_max=recommended_max,
        hard_max=hard_max,
        warnings=warnings,
    )
