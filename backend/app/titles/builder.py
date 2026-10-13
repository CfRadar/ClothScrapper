from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import yaml

from backend.app.schemas import ProductBrief, TitlePart, TitleSuggestion
from backend.app.titles.curated_titles import _adapt_curated_title_for_brief
from backend.app.titles.validator import validate_and_compose_title

_RULES: dict[str, Any] | None = None


def load_rules() -> dict[str, Any]:
    global _RULES
    if _RULES is None:
        path = Path(__file__).parent / "rules.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _RULES = yaml.safe_load(f)
        else:
            _RULES = {}
    return _RULES


def infer_attributes(brief: ProductBrief) -> dict[str, str | None]:
    """
    Infers missing attribute values from the user's brief details, extra_details,
    and tshirt_type so the resulting titles are complete and accurate.
    """
    raw_text = " ".join([
        brief.tshirt_type or "",
        brief.color or "",
        brief.gender or "",
        brief.fit or "",
        brief.fabric or "",
        brief.neck or "",
        brief.sleeve or "",
        brief.pattern or brief.print_or_design or "",
        brief.extra_details or brief.details or "",
    ]).lower()

    # 1. Garment Type
    raw_type = (brief.tshirt_type or "T-Shirt").strip()
    if not re.search(r"\b(t-shirt|tshirt|tee|tees|shirt)\b", raw_type, re.IGNORECASE):
        tshirt_type = f"{raw_type.title()} T-Shirt"
    else:
        tshirt_type = raw_type.title()

    # 2. Gender
    if brief.gender == "men":
        gender = "Men's"
    elif brief.gender == "women":
        gender = "Women's"
    elif brief.gender == "kids":
        gender = "Kids"
    else:
        gender = "Unisex"

    # 3. Fit
    fit = brief.fit.title() if brief.fit else None
    if not fit:
        if "drop shoulder" in raw_text:
            fit = "Drop Shoulder"
        elif "oversized" in raw_text or "baggy" in raw_text:
            fit = "Oversized Fit"
        elif "slim" in raw_text:
            fit = "Slim Fit"
        elif "regular" in raw_text:
            fit = "Regular Fit"

    # 4. Pattern / Print
    pattern = (brief.pattern or brief.print_or_design)
    pattern = pattern.title() if pattern else None
    if not pattern:
        if "anime" in raw_text:
            pattern = "Anime Graphic Print"
        elif "graphic" in raw_text:
            pattern = "Graphic Print"
        elif "typography" in raw_text:
            pattern = "Typography Printed"
        elif "solid" in raw_text or "plain" in raw_text:
            pattern = "Solid Plain"
        elif "striped" in raw_text:
            pattern = "Striped"
        elif "acid wash" in raw_text:
            pattern = "Acid Wash"
        elif "vintage" in raw_text:
            pattern = "Vintage Print"

    # 5. Fabric
    fabric = brief.fabric.title() if brief.fabric else None
    if not fabric:
        if "french terry" in raw_text or "terry" in raw_text:
            fabric = "French Terry Cotton"
        elif "heavy cotton" in raw_text or "heavyweight" in raw_text:
            fabric = "100% Heavy Cotton"
        elif "bio wash" in raw_text or "biowash" in raw_text:
            fabric = "Bio-Washed Cotton"
        elif "cotton" in raw_text:
            fabric = "100% Pure Cotton"
        elif "polyester" in raw_text:
            fabric = "Polyester Blend"

    # 6. Neck
    neck = brief.neck.title() if brief.neck else None
    if not neck:
        if "polo" in raw_text:
            neck = "Polo Collar"
        elif "v-neck" in raw_text or "v neck" in raw_text:
            neck = "V-Neck"
        elif "hood" in raw_text or "hooded" in raw_text:
            neck = "Hooded Neck"
        else:
            neck = "Round Neck"

    # 7. Sleeve
    sleeve = brief.sleeve.title() if brief.sleeve else None
    if not sleeve:
        if "full sleeve" in raw_text or "full" in raw_text:
            sleeve = "Full Sleeve"
        elif "sleeveless" in raw_text:
            sleeve = "Sleeveless"
        elif "drop shoulder" in raw_text:
            sleeve = "Drop Shoulder Half Sleeve"
        else:
            sleeve = "Half Sleeve"

    brand = brief.brand_name.strip() if brief.brand_name else None
    color = brief.color.title() if brief.color else "Black"
    pack = brief.pack.title() if brief.pack else None

    return {
        "brand": brand,
        "gender": gender,
        "tshirt_type": tshirt_type,
        "color": color,
        "fit": fit,
        "pattern": pattern,
        "fabric": fabric,
        "neck": neck,
        "sleeve": sleeve,
        "pack": pack,
    }


def build_fallback_titles(
    platform: str,
    brief: ProductBrief,
    platform_keywords: list[str],
    rules: dict[str, Any] | None = None,
    competitor_titles: list[str] | None = None,
) -> list[TitleSuggestion]:
    """
    Builds the three deterministic titles (search, balanced, short)
    modeled on platform formula, brief facts, top keywords, and top ranking scraped titles.
    Ensures that 3 valid titles are ALWAYS returned even if LLM fails or is empty.
    """
    if rules is None:
        rules = load_rules()

    attrs = infer_attributes(brief)
    brand = attrs["brand"]
    gender = attrs["gender"] or "Unisex"
    tshirt_type = attrs["tshirt_type"] or "Oversized T-Shirt"
    color = attrs["color"] or "Black"
    fit = attrs["fit"]
    neck = attrs["neck"]
    sleeve = attrs["sleeve"]
    fabric = attrs["fabric"]
    pattern = attrs["pattern"]
    pack = attrs["pack"]

    # Pick 2-3 words from top keywords to enrich search/balanced
    kw_words: list[str] = []
    for kw in platform_keywords[:5]:
        for w in kw.split():
            clean_w = w.strip(" ,.-").title()
            if clean_w and clean_w.lower() not in (
                "tshirt", "t-shirt", "tee", "shirt", "for", "men", "women", "black", "white"
            ):
                if clean_w not in kw_words:
                    kw_words.append(clean_w)

    feature_kw = " ".join(kw_words[:2]) if kw_words else "Trendy"

    # --- 1. SEARCH-OPTIMISED STYLE ---
    # Maximizes formula attributes and keyword density
    search_parts: list[TitlePart] = []
    if brand:
        search_parts.append(TitlePart(label="brand", text=brand))
    if platform == "meesho":
        search_parts.append(TitlePart(label="feature", text=feature_kw or "Trendy"))
    search_parts.append(TitlePart(label="gender", text=gender))
    if fit:
        search_parts.append(TitlePart(label="fit", text=fit))
    if pattern:
        search_parts.append(TitlePart(label="pattern", text=pattern))
    search_parts.append(TitlePart(label="color", text=color))
    search_parts.append(TitlePart(label="type", text=tshirt_type))
    if fabric:
        search_parts.append(TitlePart(label="fabric", text=fabric))
    if neck:
        search_parts.append(TitlePart(label="neck", text=neck))
    if sleeve:
        search_parts.append(TitlePart(label="sleeve", text=sleeve))
    if pack:
        search_parts.append(TitlePart(label="pack", text=pack))

    search_title = validate_and_compose_title(
        search_parts,
        style="search",
        platform=platform,
        brief=brief,
        platform_keywords=platform_keywords,
        rules=rules,
    )

    # If top scraped competitor titles exist and search_title is too short for Amazon,
    # benchmark against the top ranking competitor title
    if platform == "amazon" and search_title.length < 80 and competitor_titles:
        for comp in competitor_titles:
            adapted = _adapt_curated_title_for_brief(comp, brief)
            if 80 <= len(adapted) <= 180:
                # Use adapted competitor title as high-performing benchmark
                search_title = TitleSuggestion(
                    style="search",
                    title=adapted,
                    text=adapted,
                    length=len(adapted),
                    parts=search_parts,
                    warnings=[],
                )
                break

    # --- 2. BALANCED STYLE ---
    # High-CTR readable combination of essential brief facts and primary keyword
    balanced_parts: list[TitlePart] = []
    if brand:
        balanced_parts.append(TitlePart(label="brand", text=brand))
    if platform == "meesho":
        balanced_parts.append(TitlePart(label="feature", text="Stylish"))
    balanced_parts.append(TitlePart(label="gender", text=gender))
    if pattern:
        balanced_parts.append(TitlePart(label="pattern", text=pattern))
    balanced_parts.append(TitlePart(label="color", text=color))
    if fit:
        balanced_parts.append(TitlePart(label="fit", text=fit))
    balanced_parts.append(TitlePart(label="type", text=tshirt_type))
    if neck:
        balanced_parts.append(TitlePart(label="neck", text=neck))

    balanced_title = validate_and_compose_title(
        balanced_parts,
        style="balanced",
        platform=platform,
        brief=brief,
        platform_keywords=platform_keywords,
        rules=rules,
    )

    # --- 3. SHORT STYLE ---
    # Minimalist mobile-friendly: Brand + Gender + Color + Pattern + Type
    short_parts: list[TitlePart] = []
    if brand:
        short_parts.append(TitlePart(label="brand", text=brand))
    short_parts.append(TitlePart(label="gender", text=gender))
    short_parts.append(TitlePart(label="color", text=color))
    if pattern and platform != "myntra":
        short_parts.append(TitlePart(label="pattern", text=pattern))
    short_parts.append(TitlePart(label="type", text=tshirt_type))

    short_title = validate_and_compose_title(
        short_parts,
        style="short",
        platform=platform,
        brief=brief,
        platform_keywords=platform_keywords,
        rules=rules,
    )

    return [search_title, balanced_title, short_title]
