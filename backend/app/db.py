import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from backend.app.config import get_settings

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    ttl_seconds INT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_usage (
    day TEXT NOT NULL,
    model TEXT NOT NULL,
    count INT NOT NULL DEFAULT 0,
    PRIMARY KEY(day, model)
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    brief_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    created_at REAL NOT NULL,
    run_token TEXT
);

CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    strategy_used TEXT,
    failure_cause TEXT,
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_ok_at REAL,
    last_checked_at REAL NOT NULL
);
"""


def get_db_path() -> str:
    settings = get_settings()
    db_path = settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path


def secure_file_permissions(filepath: str) -> None:
    """Sets 600 permissions on POSIX systems if file exists."""
    try:
        if os.path.exists(filepath) and os.name != "nt":
            os.chmod(filepath, 0o600)
    except Exception:
        pass


@asynccontextmanager
async def get_db(db_path: str | None = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    target_path = db_path or get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    async with aiosqlite.connect(target_path) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


async def init_db(db_path: str | None = None) -> None:
    target_path = db_path or get_db_path()
    async with get_db(target_path) as conn:
        await conn.executescript(SCHEMA_SQL)
        # Handle migration if runs table existed without run_token
        try:
            await conn.execute("ALTER TABLE runs ADD COLUMN run_token TEXT")
            await conn.commit()
        except Exception:
            pass
    secure_file_permissions(target_path)
