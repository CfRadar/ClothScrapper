import time
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PlatformName = Literal["amazon", "myntra", "flipkart"]


class ProductBrief(BaseModel):
    platforms: list[PlatformName] = Field(min_length=1)
    tshirt_type: str = Field(description="e.g. oversized graphic tee")
    color: str
    gender: Literal["men", "women", "unisex", "kids"] = "unisex"
    fit: str | None = None
    fabric: str | None = None
    neck: str | None = None
    sleeve: str | None = None
    print_or_design: str | None = None
    occasion: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    sizes: str | None = None
    brand_name: str | None = None
    extra_details: str | None = None  # Free-text additional seller details


class TargetMarket(BaseModel):
    age_range: str
    personas: list[str]
    interests: list[str]
    regions: list[str]
    language_notes: str  # e.g. Hinglish usage notes


class SearchPlan(BaseModel):
    target_market: TargetMarket
    marketplace_queries: dict[PlatformName, list[str]]
    social_queries: list[str]
    seed_keywords: list[str]


class ScrapedProduct(BaseModel):
    platform: PlatformName
    title: str
    brand: str | None = None
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int
    sponsored: bool = False
    url: str


class PlatformScrape(BaseModel):
    platform: PlatformName
    status: Literal["ok", "partial", "blocked", "error", "cached"]
    products: list[ScrapedProduct] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    related_searches: list[str] = Field(default_factory=list)
    note: str | None = None


class SocialSignal(BaseModel):
    source: Literal["reddit", "x", "instagram"]
    phrase: str
    mentions: int = 1
    sample_titles: list[str] = Field(default_factory=list)


class SocialScrape(BaseModel):
    signals: list[SocialSignal] = Field(default_factory=list)
    statuses: dict[str, Literal["ok", "skipped", "blocked", "error"]] = Field(default_factory=dict)
    candidate_keywords: list[str] = Field(default_factory=list)


class PlatformKeywords(BaseModel):
    platform: PlatformName
    keywords: list[str] = Field(description="ONLY keywords, ordered best-first, 15-25 items")


class PlatformFactors(BaseModel):
    title_formula: str
    recommended_title_example: str
    attributes_to_fill: list[str]
    price_band: str
    negative_keywords: list[str]
    hashtags_or_tags: list[str]
    competition_note: str
    seasonality_note: str


class OtherFactors(BaseModel):
    target_market_summary: str
    per_platform: dict[PlatformName, PlatformFactors]
    general: list[str]

    @field_validator("per_platform", mode="before")
    @classmethod
    def coerce_per_platform(cls, val: Any) -> Any:
        if isinstance(val, dict):
            new_val = {}
            for k, v in val.items():
                if isinstance(v, str):
                    new_val[k] = PlatformFactors(
                        title_formula="[Brand] + [Fit] + [Neck/Style] + [Color] + [Fabric] + T-Shirt",
                        recommended_title_example=f"Premium {k.title()} Graphic T-Shirt",
                        attributes_to_fill=["Fit", "Neck", "Fabric", "Occasion"],
                        price_band="₹499 - ₹899",
                        negative_keywords=["cheap", "free", "fake"],
                        hashtags_or_tags=["#tshirt", "#fashion"],
                        competition_note=v,
                        seasonality_note="All-season demand",
                    )
                elif isinstance(v, dict):
                    v.setdefault(
                        "title_formula",
                        "[Brand] + [Fit] + [Neck/Style] + [Color] + [Fabric] + T-Shirt",
                    )
                    v.setdefault(
                        "recommended_title_example", f"Premium {k.title()} Graphic T-Shirt"
                    )
                    v.setdefault("attributes_to_fill", ["Fit", "Neck", "Fabric", "Occasion"])
                    v.setdefault("price_band", "₹499 - ₹899")
                    v.setdefault("negative_keywords", ["cheap", "free", "fake"])
                    v.setdefault("hashtags_or_tags", ["#tshirt", "#fashion"])
                    v.setdefault("competition_note", "Moderate competition")
                    v.setdefault("seasonality_note", "All-season demand")
                    new_val[k] = v
                else:
                    new_val[k] = v
            return new_val
        return val


class RunResult(BaseModel):
    run_id: str
    keywords: list[PlatformKeywords]
    other_factors: OtherFactors
    platform_statuses: dict[str, str]
    llm_calls_used: int


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    keywords_patch: list[PlatformKeywords] | None = None
    factors_patch: dict | None = None

    @field_validator("keywords_patch", mode="before")
    @classmethod
    def coerce_keywords_patch(cls, val: Any) -> Any:
        if isinstance(val, dict):
            return [
                PlatformKeywords(platform=k, keywords=v if isinstance(v, list) else [str(v)])
                for k, v in val.items()
            ]
        return val


class SSEEvent(BaseModel):
    type: Literal["stage", "progress", "warning", "result", "error", "done"]
    stage: Literal["planner", "marketplace", "social", "analyst", "system"]
    message: str
    data: dict | None = None
    ts: float = Field(default_factory=time.time)
