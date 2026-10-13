from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from datetime import datetime

class Item(BaseModel):
    title: str
    brand: str = ""
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    position: int = 0
    sponsored: bool = False
    url: str = ""
    source_id: str
    b2b: dict[str, Any] | None = None  # supplier, location, moq, unit, price_range

class SourceResult(BaseModel):
    source_id: str
    status: str  # ok | empty | blocked | degraded | error
    strategy_used: str  # suggestion_api | embedded_state | network_capture | dom_selector | heuristic
    items: list[Item] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    item_count: int = 0
    duration_ms: float = 0.0
    failure_cause: str | None = None
    note: str | None = None

class HealthReport(BaseModel):
    source_id: str
    status: str  # healthy | degraded | blocked | unavailable | disabled | unknown
    strategy_used: str | None = None
    failure_cause: str | None = None
    consecutive_failures: int = 0
    last_ok_at: datetime | None = None
    last_checked_at: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float = 0.0
    details: str = ""

@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol defining the interface for all marketplace, B2B, quick commerce, and signal sources."""
    id: str
    group: str       # marketplaces | b2b | quickcommerce | signals
    kind: str        # marketplace | b2b | quickcommerce | search | social
    roles: list[str] # sell_target | signal

    async def search(self, query: str, ctx: Any) -> SourceResult:
        """Search the source for product listings or keyword signals."""
        ...

    async def suggest(self, query: str, ctx: Any) -> list[str]:
        """Fetch search suggestions or autocomplete phrases for a given prefix query."""
        ...

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        """Pure deterministic parser turning HTML or JSON into validated Item objects."""
        ...

    async def healthcheck(self, ctx: Any) -> HealthReport:
        """Run a lightweight canary check to report source operational status."""
        ...


class BaseSourceAdapter:
    """Base class providing standard strategy ladder and error handling routines."""

    def __init__(self, source_id: str, group: str, kind: str, roles: list[str]):
        self.id = source_id
        self.group = group
        self.kind = kind
        self.roles = roles

    def parse(self, raw: str | dict[str, Any]) -> list[Item]:
        raise NotImplementedError("Adapters must implement pure parse method.")

    async def search(self, query: str, ctx: Any) -> SourceResult:
        raise NotImplementedError("Adapters must implement async search method.")

    async def suggest(self, query: str, ctx: Any) -> list[str]:
        return []

    async def healthcheck(self, ctx: Any) -> HealthReport:
        try:
            start = datetime.utcnow()
            suggestions = await self.suggest("t-shirt", ctx)
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            if suggestions:
                return HealthReport(
                    source_id=self.id,
                    status="healthy",
                    strategy_used="suggestion_api",
                    latency_ms=latency,
                    details=f"Returned {len(suggestions)} suggestions."
                )
            return HealthReport(
                source_id=self.id,
                status="degraded",
                latency_ms=latency,
                details="Zero suggestions returned on canary query."
            )
        except Exception as e:
            return HealthReport(
                source_id=self.id,
                status="degraded",
                failure_cause=str(e),
                details=f"Canary error: {e}"
            )
