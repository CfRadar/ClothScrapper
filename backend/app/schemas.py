import re
import time
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PlatformName = Literal["amazon", "myntra", "flipkart", "meesho"]
NodeId = str

NodeStatus = Literal["queued", "running", "success", "warning", "error", "skipped", "cached"]

# Regex patterns for input validation and sanitization
CONTROL_AND_ZERO_WIDTH_REGEX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200d\ufeff]")
URL_SCHEME_REGEX = re.compile(r"(?:https?|ftp|javascript|data|file):", re.IGNORECASE)


def sanitize_text(val: str | None, max_len: int = 120, allow_newline: bool = False) -> str | None:
    if val is None:
        return None
    # Reject control and zero-width characters
    if CONTROL_AND_ZERO_WIDTH_REGEX.search(val):
        raise ValueError("Control and zero-width characters are not permitted.")
    val = val.strip()
    if not allow_newline:
        val = " ".join(val.split())
    # Reject HTML tags / injection delimiters
    if "<" in val or ">" in val:
        raise ValueError("Characters '<' and '>' are not permitted.")
    # Reject URL schemes
    if URL_SCHEME_REGEX.search(val):
        raise ValueError("URL schemes are not permitted in brief fields.")
    if len(val) > max_len:
        raise ValueError(f"Value exceeds maximum length of {max_len} characters.")
    return val


class ProductBrief(BaseModel):
    platforms: list[PlatformName] = Field(
        default_factory=lambda: ["amazon", "myntra", "flipkart", "meesho"], min_length=1
    )
    research_sources: list[str] = Field(
        default_factory=lambda: ["google", "pinterest", "reddit"]
    )
    tshirt_type: str = Field(description="e.g. oversized graphic tee", max_length=60)
    color: str = Field(max_length=60)
    gender: Literal["men", "women", "unisex", "kids"] = "unisex"
    fit: str | None = Field(default=None, max_length=120)
    fabric: str | None = Field(default=None, max_length=120)
    neck: str | None = Field(default=None, max_length=120)
    sleeve: str | None = Field(default=None, max_length=120)
    print_or_design: str | None = Field(default=None, max_length=120)
    pattern: str | None = Field(default=None, max_length=120)
    occasion: str | None = Field(default=None, max_length=120)
    price_min: int | None = Field(default=None, ge=0, le=100000)
    price_max: int | None = Field(default=None, ge=0, le=100000)
    sizes: str | None = Field(default=None, max_length=120)
    brand_name: str | None = Field(default=None, max_length=120)
    pack: str | None = Field(default=None, max_length=60)
    size_range: str | None = Field(default=None, max_length=60)
    extra_details: str | None = Field(default=None, max_length=1000)
    details: str | None = Field(default=None, max_length=1000)

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, platforms: list[PlatformName]) -> list[PlatformName]:
        unique_platforms = list(dict.fromkeys(platforms))
        if len(unique_platforms) > 4:
            raise ValueError("At most 4 unique platforms can be selected.")
        return unique_platforms

    @field_validator("tshirt_type", "color")
    @classmethod
    def sanitize_short_required(cls, v: str) -> str:
        res = sanitize_text(v, max_len=60)
        if not res:
            raise ValueError("Field cannot be empty.")
        return res

    @field_validator(
        "fit",
        "fabric",
        "neck",
        "sleeve",
        "print_or_design",
        "pattern",
        "occasion",
        "sizes",
        "brand_name",
        "pack",
        "size_range",
    )
    @classmethod
    def sanitize_short_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        res = sanitize_text(v, max_len=120)
        return res if res else None

    @field_validator("extra_details", "details")
    @classmethod
    def sanitize_extra_details(cls, v: str | None) -> str | None:
        if v is None:
            return None
        res = sanitize_text(v, max_len=1000, allow_newline=True)
        return res if res else None

    @model_validator(mode="after")
    def sync_pattern_and_validate_prices(self) -> "ProductBrief":
        if self.pattern and not self.print_or_design:
            self.print_or_design = self.pattern
        elif self.print_or_design and not self.pattern:
            self.pattern = self.print_or_design

        if self.details and not self.extra_details:
            self.extra_details = self.details
        elif self.extra_details and not self.details:
            self.details = self.extra_details

        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min cannot be greater than price_max.")
        return self


class TargetMarket(BaseModel):
    age_range: str
    personas: list[str]
    interests: list[str]
    regions: list[str]
    language_notes: str


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
    status: Literal["ok", "partial", "blocked", "error", "cached", "skipped", "unavailable"]
    products: list[ScrapedProduct] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    related_searches: list[str] = Field(default_factory=list)
    note: str | None = None


class SocialSignal(BaseModel):
    source: str
    phrase: str
    mentions: int = 1
    sample_titles: list[str] = Field(default_factory=list)


class SocialScrape(BaseModel):
    signals: list[SocialSignal] = Field(default_factory=list)
    statuses: dict[str, Literal["ok", "skipped", "blocked", "error"]] = Field(default_factory=dict)
    candidate_keywords: list[str] = Field(default_factory=list)


TitleStyle = Literal["search", "balanced", "short"]
PartLabel = Literal[
    "brand",
    "gender",
    "type",
    "fit",
    "fabric",
    "neck",
    "sleeve",
    "pattern",
    "color",
    "size",
    "pack",
    "occasion",
    "feature",
]


class TitlePart(BaseModel):
    label: PartLabel
    text: str


class TitleSuggestion(BaseModel):
    style: TitleStyle
    parts: list[TitlePart] = Field(default_factory=list)
    text: str = ""
    title: str = ""
    length: int = 0
    recommended_max: int = 150
    hard_max: int = 200
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_title_and_text(self) -> "TitleSuggestion":
        if self.text and not self.title:
            self.title = self.text
        elif self.title and not self.text:
            self.text = self.title
        if not self.length:
            self.length = len(self.title or self.text)
        return self


class CompetitorTitle(BaseModel):
    rank: int
    title: str
    brand: str | None = None
    price: str | float | None = None
    rating: float | None = None
    reviews_count: int | None = None
    rating_count: int | None = None
    length: int = 0

    @model_validator(mode="after")
    def compute_length_and_sync_reviews(self) -> "CompetitorTitle":
        if not self.length and self.title:
            self.length = len(self.title)
        if self.reviews_count and not self.rating_count:
            self.rating_count = self.reviews_count
        elif self.rating_count and not self.reviews_count:
            self.reviews_count = self.rating_count
        return self


class PlatformDetails(BaseModel):
    attributes_to_fill: list[str] = Field(default_factory=list)
    price_band: str = ""
    negative_keywords: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    competition_note: str = ""
    seasonality_note: str = ""
    notes: list[str] = Field(default_factory=list)


class PlatformResult(BaseModel):
    platform: PlatformName
    keywords: list[str] = Field(description="ONLY keywords, best first, 15-25 items")
    titles: list[TitleSuggestion] = Field(description="Exactly 3 titles (search, balanced, short)")
    top_scraped_titles: list[CompetitorTitle] = Field(
        default_factory=list,
        description="Top 10 scraped ranking competitor listing titles from search results",
    )
    details: PlatformDetails
    warning: str | None = None


# Kept for backward compatibility in scoring/analyst subcomponents
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
    demand_signals: list[str] = Field(default_factory=list)
    moq_and_supplier_notes: list[str] = Field(default_factory=list)


class RunResult(BaseModel):
    run_id: str
    target_market_summary: str
    platforms: list[PlatformResult]
    llm_calls_used: int
    nodes_snapshot: dict[str, dict] | None = None


class ChatRequest(BaseModel):
    message: str = Field(max_length=1000)

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Strip control characters
        cleaned = CONTROL_AND_ZERO_WIDTH_REGEX.sub("", v).strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        if len(cleaned) > 1000:
            raise ValueError("Message exceeds 1000 characters.")
        return cleaned


class ChatResponse(BaseModel):
    reply: str
    patch: list[PlatformResult] | None = None


class NodeEvent(BaseModel):
    type: Literal["node"] = "node"
    seq: int
    node_id: NodeId
    status: NodeStatus
    detail: str | None = None
    metrics: dict[str, str | int | float] | None = None
    ts: float = Field(default_factory=time.time)


class SSEEvent(BaseModel):
    seq: int = 0
    type: Literal["stage", "progress", "warning", "result", "error", "done", "node"]
    stage: Literal["planner", "marketplace", "social", "analyst", "system"] | None = None
    message: str | None = None
    data: dict | None = None
    node_id: NodeId | None = None
    status: NodeStatus | None = None
    detail: str | None = None
    metrics: dict[str, str | int | float] | None = None
    ts: float = Field(default_factory=time.time)
