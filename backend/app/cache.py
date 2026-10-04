import json
import time
from typing import Any

from backend.app.config import get_settings
from backend.app.db import get_db


async def get(key: str, db_path: str | None = None) -> Any | None:
    """Retrieve value from cache if exists and not expired."""
    now = time.time()
    async with get_db(db_path) as conn:
        async with conn.execute(
            "SELECT value_json, created_at, ttl_seconds FROM cache WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            value_json = row["value_json"]
            created_at = row["created_at"]
            ttl_seconds = row["ttl_seconds"]

            if now > created_at + ttl_seconds:
                # Expired - clean up asynchronously
                await conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                await conn.commit()
                return None

            try:
                return json.loads(value_json)
            except Exception:
                return value_json


async def set(key: str, value: Any, ttl: int | None = None, db_path: str | None = None) -> None:
    """Store value in cache with TTL."""
    settings = get_settings()
    ttl_seconds = ttl if ttl is not None else settings.CACHE_TTL_SECONDS
    now = time.time()
    value_json = json.dumps(value) if not isinstance(value, str) else value

    async with get_db(db_path) as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO cache (key, value_json, created_at, ttl_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (key, value_json, now, ttl_seconds),
        )
        await conn.commit()


async def delete(key: str, db_path: str | None = None) -> None:
    """Remove key from cache."""
    async with get_db(db_path) as conn:
        await conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        await conn.commit()
