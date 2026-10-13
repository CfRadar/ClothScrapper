import re
from typing import Any
from backend.app.schemas import TitlePart

SMALL_WORDS = {"and", "for", "with", "of", "in", "the", "a", "an", "on", "by", "to"}


def to_title_case(text: str) -> str:
    """Format title text cleanly with proper capitalization without breaking abbreviations."""
    words = text.strip().split()
    result = []
    for idx, w in enumerate(words):
        upper_w = w.upper()
        # Keep common abbreviations like GSM, 240GSM, T-SHIRT, etc.
        if any(c.isupper() for c in w[1:]) and not w.isupper():
            result.append(w)
        elif upper_w in ("GSM", "COTTON", "OVERSIZED", "TEE", "T-SHIRT"):
            if upper_w == "T-SHIRT":
                result.append("T-Shirt")
            elif upper_w == "GSM":
                result.append("GSM")
            else:
                result.append(w.capitalize())
        elif re.match(r"^\d+GSM$", upper_w):
            result.append(upper_w)
        elif idx > 0 and w.lower() in SMALL_WORDS:
            result.append(w.lower())
        else:
            # Handle hyphenated words like Drop-Shoulder, Acid-Wash
            if "-" in w:
                result.append("-".join(part.capitalize() for part in w.split("-")))
            else:
                result.append(w.capitalize())
    return " ".join(result)


def compose_title(
    parts: list[TitlePart],
    platform: str,
    rules: dict[str, Any],
) -> tuple[str, list[TitlePart]]:
    """
    Joins parts in the platform formula order, applies casing rules,
    removes duplicate words (case-insensitive) keeping the first,
    and collapses whitespace.
    """
    plat_rule = rules.get("platforms", {}).get(platform, {})
    formula_order = plat_rule.get("formula", [])

    # Order parts matching formula
    ordered_parts: list[TitlePart] = []
    seen_labels: set[str] = set()

    for label in formula_order:
        for p in parts:
            if p.label == label and label not in seen_labels and p.text and p.text.strip():
                ordered_parts.append(TitlePart(label=p.label, text=p.text.strip()))
                seen_labels.add(label)
                break

    # Add any remaining non-duplicate parts that were not in formula
    for p in parts:
        if p.label not in seen_labels and p.text and p.text.strip():
            ordered_parts.append(TitlePart(label=p.label, text=p.text.strip()))
            seen_labels.add(p.label)

    # Word deduplication while composing text
    seen_words: set[str] = set()
    deduped_tokens: list[str] = []

    for part in ordered_parts:
        tokens = part.text.split()
        for tok in tokens:
            cleaned_tok = tok.strip(" ,.-/()").lower()
            if not cleaned_tok:
                continue
            if cleaned_tok not in seen_words:
                seen_words.add(cleaned_tok)
                deduped_tokens.append(tok)

    raw_text = " ".join(deduped_tokens)
    casing = plat_rule.get("case", "title")

    if casing == "title":
        final_text = to_title_case(raw_text)
    else:
        final_text = raw_text.strip()

    # Final whitespace collapse
    final_text = re.sub(r"\s+", " ", final_text).strip()

    return final_text, ordered_parts
