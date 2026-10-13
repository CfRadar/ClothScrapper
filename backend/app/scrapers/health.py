"""
Health tracking and circuit breaker for data sources.
Persists status in SQLite `source_health` table.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

try:
    from backend.app.db import get_db
except ImportError:
    from app.db import get_db

logger = logging.getLogger("backend.scrapers.health")

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_TIMEOUT_SECONDS = 1800  # 30 minutes


class HealthRecord(BaseModel):
    source_id: str
    status: Literal["healthy", "degraded", "blocked", "unavailable", "disabled", "unknown"]
    strategy_used: str | None = None
    failure_cause: str | None = None
    consecutive_failures: int = 0
    last_ok_at: float | None = None
    last_checked_at: float = Field(default_factory=time.time)
    circuit_breaker_open: bool = False


def map_result_status_to_health(
    result_status: str,
    status_override: str | None = None,
) -> tuple[Literal["healthy", "degraded", "blocked", "unavailable", "disabled", "unknown"], bool]:
    """
    Maps SourceResult.status to HealthRecord.status.
    Returns (health_status, is_success).
    """
    if status_override:
        if status_override == "unavailable":
            return "unavailable", False
        if status_override == "disabled":
            return "disabled", False

    if result_status in ("ok", "cached"):
        return "healthy", True
    elif result_status == "partial":
        return "degraded", True
    elif result_status == "blocked":
        return "blocked", False
    elif result_status in ("unavailable",):
        return "unavailable", False
    elif result_status in ("needs_location", "error"):
        return "degraded", False
    elif result_status == "skipped":
        return "degraded", False
    return "unknown", False


async def _ensure_health_table(conn) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_health (
            source_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            strategy_used TEXT,
            failure_cause TEXT,
            consecutive_failures INT NOT NULL DEFAULT 0,
            last_ok_at REAL,
            last_checked_at REAL NOT NULL
        )
        """
    )


async def record_health(
    source_id: str,
    result_status: str,
    strategy_used: str | None = None,
    failure_cause: str | None = None,
    status_override: str | None = None,
    db_path: str | None = None,
) -> HealthRecord:
    """
    Updates the health status of a source after an execution or canary probe.
    """
    now = time.time()
    health_status, is_success = map_result_status_to_health(result_status, status_override)

    async with get_db(db_path) as conn:
        await _ensure_health_table(conn)
        async with conn.execute(
            "SELECT consecutive_failures, last_ok_at FROM source_health WHERE source_id = ?",
            (source_id,),
        ) as cursor:
            row = await cursor.fetchone()

        prev_failures = row["consecutive_failures"] if row else 0
        last_ok_at = row["last_ok_at"] if row else None

        if is_success:
            consecutive_failures = 0
            last_ok_at = now
        elif result_status == "skipped":
            consecutive_failures = prev_failures
        else:
            consecutive_failures = prev_failures + 1

        await conn.execute(
            """
            INSERT INTO source_health (
                source_id, status, strategy_used, failure_cause,
                consecutive_failures, last_ok_at, last_checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                status = excluded.status,
                strategy_used = excluded.strategy_used,
                failure_cause = excluded.failure_cause,
                consecutive_failures = excluded.consecutive_failures,
                last_ok_at = coalesce(excluded.last_ok_at, source_health.last_ok_at),
                last_checked_at = excluded.last_checked_at
            """,
            (
                source_id,
                health_status,
                strategy_used,
                failure_cause,
                consecutive_failures,
                last_ok_at,
                now,
            ),
        )
        await conn.commit()

    breaker_open = (
        consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD
        and (now - now) < CIRCUIT_BREAKER_TIMEOUT_SECONDS
    )

    return HealthRecord(
        source_id=source_id,
        status=health_status,
        strategy_used=strategy_used,
        failure_cause=failure_cause,
        consecutive_failures=consecutive_failures,
        last_ok_at=last_ok_at,
        last_checked_at=now,
        circuit_breaker_open=breaker_open,
    )


async def is_circuit_breaker_open(source_id: str, db_path: str | None = None) -> bool:
    """
    Checks if a source's circuit breaker is open (3 consecutive failures within 30 minutes).
    """
    now = time.time()
    async with get_db(db_path) as conn:
        await _ensure_health_table(conn)
        async with conn.execute(
            "SELECT consecutive_failures, last_checked_at FROM source_health WHERE source_id = ?",
            (source_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False

            failures = row["consecutive_failures"]
            last_checked = row["last_checked_at"]

            if failures >= CIRCUIT_BREAKER_THRESHOLD and (now - last_checked) < CIRCUIT_BREAKER_TIMEOUT_SECONDS:
                logger.warning(
                    f"Circuit breaker OPEN for source '{source_id}': "
                    f"{failures} consecutive failures. Skipping execution."
                )
                return True
            return False


async def reset_circuit_breaker(source_id: str | None = None, db_path: str | None = None) -> None:
    """Resets consecutive failures and re-enables a source (or all sources)."""
    async with get_db(db_path) as conn:
        await _ensure_health_table(conn)
        if source_id:
            await conn.execute(
                "UPDATE source_health SET consecutive_failures = 0, status = 'healthy' WHERE source_id = ?",
                (source_id,),
            )
        else:
            await conn.execute("UPDATE source_health SET consecutive_failures = 0, status = 'healthy'")
        await conn.commit()


async def get_source_health(source_id: str, db_path: str | None = None) -> HealthRecord | None:
    now = time.time()
    async with get_db(db_path) as conn:
        await _ensure_health_table(conn)
        async with conn.execute(
            """
            SELECT source_id, status, strategy_used, failure_cause,
                   consecutive_failures, last_ok_at, last_checked_at
            FROM source_health WHERE source_id = ?
            """,
            (source_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            failures = row["consecutive_failures"]
            last_checked = row["last_checked_at"]
            is_open = (
                failures >= CIRCUIT_BREAKER_THRESHOLD
                and (now - last_checked) < CIRCUIT_BREAKER_TIMEOUT_SECONDS
            )

            return HealthRecord(
                source_id=row["source_id"],
                status=row["status"],
                strategy_used=row["strategy_used"],
                failure_cause=row["failure_cause"],
                consecutive_failures=failures,
                last_ok_at=row["last_ok_at"],
                last_checked_at=last_checked,
                circuit_breaker_open=is_open,
            )


async def get_all_source_health(db_path: str | None = None) -> dict[str, HealthRecord]:
    now = time.time()
    records: dict[str, HealthRecord] = {}
    async with get_db(db_path) as conn:
        await _ensure_health_table(conn)
        async with conn.execute(
            """
            SELECT source_id, status, strategy_used, failure_cause,
                   consecutive_failures, last_ok_at, last_checked_at
            FROM source_health
            """
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                failures = row["consecutive_failures"]
                last_checked = row["last_checked_at"]
                is_open = (
                    failures >= CIRCUIT_BREAKER_THRESHOLD
                    and (now - last_checked) < CIRCUIT_BREAKER_TIMEOUT_SECONDS
                )
                records[row["source_id"]] = HealthRecord(
                    source_id=row["source_id"],
                    status=row["status"],
                    strategy_used=row["strategy_used"],
                    failure_cause=row["failure_cause"],
                    consecutive_failures=failures,
                    last_ok_at=row["last_ok_at"],
                    last_checked_at=last_checked,
                    circuit_breaker_open=is_open,
                )
    return records
