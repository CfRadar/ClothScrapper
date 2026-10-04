from datetime import date

from backend.app.config import get_settings
from backend.app.db import get_db


def get_today_str() -> str:
    return date.today().isoformat()


async def get_today_used(db_path: str | None = None) -> int:
    """Calculate total LLM calls consumed today."""
    today = get_today_str()
    async with get_db(db_path) as conn:
        async with conn.execute(
            "SELECT SUM(count) as total FROM llm_usage WHERE day = ?", (today,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["total"] is not None:
                return int(row["total"])
            return 0


async def remaining_today(db_path: str | None = None, daily_limit: int | None = None) -> int:
    """Return remaining calls for today before hitting the free tier daily limit."""
    settings = get_settings()
    limit = daily_limit if daily_limit is not None else settings.LLM_DAILY_LIMIT
    used = await get_today_used(db_path)
    return max(0, limit - used)


async def can_call(db_path: str | None = None, daily_limit: int | None = None) -> bool:
    """Check if at least one call remains within today's quota."""
    return (await remaining_today(db_path, daily_limit=daily_limit)) > 0


async def record(model: str, db_path: str | None = None) -> None:
    """Record a completed LLM invocation against the quota."""
    today = get_today_str()
    async with get_db(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO llm_usage (day, model, count)
            VALUES (?, ?, 1)
            ON CONFLICT(day, model) DO UPDATE SET count = count + 1
            """,
            (today, model),
        )
        await conn.commit()


async def get_model_breakdown(db_path: str | None = None) -> dict[str, int]:
    """Return today's usage grouped by model."""
    today = get_today_str()
    async with get_db(db_path) as conn:
        async with conn.execute(
            "SELECT model, count FROM llm_usage WHERE day = ?", (today,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row["model"]: row["count"] for row in rows}
