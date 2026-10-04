---
name: sqlite-cache-and-quota
description: Manages SQLite database schema, aiosqlite async operations, 24-hour scraping caching, and daily LLM quota tracking. Use when implementing or querying database persistence, checking remaining OpenRouter calls, or caching scrape and social listener results.
---

# SQLite Cache and Quota

## Purpose
This skill defines the schema and asynchronous operations for the local SQLite database (`aiosqlite`). It establishes a transparent 24-hour cache for marketplace and social scrapers to prevent redundant network requests and enforces a strict daily quota guard to ensure the application stays within OpenRouter's free daily call limits.

## When to use
- When initializing the SQLite database tables on application startup.
- When saving or checking cached scrape results for Amazon, Myntra, Flipkart, or Reddit.
- Before executing an LLM call to verify if the daily budget (`can_call()`) is exhausted.
- Immediately after executing an LLM call to record token/model usage (`record_call(model)`).
- When exposing backend `/api/quota` telemetry to the frontend.
- When inspecting database health via `scripts/inspect_db.py`.

## Step-by-step procedure

1. **Initialize Database Schema (`aiosqlite`)**:
   - Establish table definitions during the FastAPI lifespan startup event:
     ```sql
     CREATE TABLE IF NOT EXISTS cache (
         key TEXT PRIMARY KEY,
         value_json TEXT NOT NULL,
         created_at INTEGER NOT NULL,
         ttl_seconds INTEGER NOT NULL DEFAULT 86400
     );

     CREATE TABLE IF NOT EXISTS llm_usage (
         day TEXT NOT NULL,
         model TEXT NOT NULL,
         count INTEGER NOT NULL DEFAULT 0,
         PRIMARY KEY (day, model)
     );

     CREATE TABLE IF NOT EXISTS runs (
         id TEXT PRIMARY KEY,
         brief_json TEXT NOT NULL,
         status TEXT NOT NULL,
         result_json TEXT,
         created_at TEXT NOT NULL
     );

     CREATE TABLE IF NOT EXISTS scrape_log (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         platform TEXT NOT NULL,
         query TEXT NOT NULL,
         status TEXT NOT NULL,
         result_count INTEGER NOT NULL DEFAULT 0,
         created_at TEXT NOT NULL
     );
     ```

2. **Standardize Cache Keys and Enforce 24h TTL**:
   - Normalize queries before constructing keys: lowercase, remove special characters, trim whitespace, and sort multiple terms.
   - Marketplace cache key formula: `scrape:{platform}:{normalized_query}`
     - Example: `scrape:amazon:mens_oversized_cotton_tshirt`
     - Example: `scrape:myntra:black_drop_shoulder_tee`
   - Social cache key formula: `social:{source}:{normalized_query}`
     - Example: `social:reddit:indianstreetwear_oversized_tshirt`
   - Default TTL: 86,400 seconds (24 hours).
   - Read logic: Query `SELECT value_json FROM cache WHERE key = ? AND (created_at + ttl_seconds) > ?`. If present, deserialize JSON and bypass scraper execution.
   - Write logic: `INSERT OR REPLACE INTO cache (key, value_json, created_at, ttl_seconds) VALUES (?, ?, ?, ?)`.

3. **Implement Daily Quota Guard**:
   - The quota guard tracks total LLM invocations per local calendar day (`YYYY-MM-DD`).
   - Define daily hard limit in configuration (e.g., `MAX_DAILY_LLM_CALLS=150`).
   - **`can_call() -> bool`**:
     - Query `SELECT SUM(count) FROM llm_usage WHERE day = date('now', 'localtime')`.
     - Return `True` if `total < MAX_DAILY_LLM_CALLS`, otherwise `False`.
   - **`record_call(model: str) -> None`**:
     - Execute:
       ```sql
       INSERT INTO llm_usage (day, model, count)
       VALUES (date('now', 'localtime'), ?, 1)
       ON CONFLICT(day, model) DO UPDATE SET count = count + 1;
       ```
   - **`remaining_today() -> int`**:
     - Return `max(0, MAX_DAILY_LLM_CALLS - total_used)`.

4. **Persist Runs and Scrape Telemetry**:
   - Save agent pipeline run state transitions: `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED`.
   - Record scrape successes, blocks, and item counts in `scrape_log` for debugging and polite rate tuning.

5. **Periodic Cache Pruning**:
   - Run lightweight background cleanup once per day or on startup:
     `DELETE FROM cache WHERE (created_at + ttl_seconds) < strftime('%s', 'now');`

## Rules (do / don't)
- **DO** use async `aiosqlite` for all database interactions to avoid blocking FastAPI's event loop.
- **DO** normalize all cache query keys (lowercase, strip symbols) to maximize cache hit ratio.
- **DO** reset daily counters using the local calendar day (`localtime`).
- **DO** always check `can_call()` before initiating Planner or Analyst LLM calls.
- **DON'T** perform synchronous `sqlite3` queries inside async FastAPI route handlers or agent tasks.
- **DON'T** let the cache grow indefinitely without TTL expiration checks.
- **DON'T** hardcode DB paths; read from `DATABASE_URL` or configuration settings (`backend/data/app.db`).

## Examples

### Async Cache & Quota Manager Implementation
```python
import time
import json
from datetime import date
import aiosqlite

class QuotaExceededException(Exception):
    pass

class DatabaseManager:
    def __init__(self, db_path: str, max_daily_calls: int = 150):
        self.db_path = db_path
        self.max_daily_calls = max_daily_calls

    async def get_cached(self, key: str) -> dict | None:
        now = int(time.time())
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value_json FROM cache WHERE key = ? AND (created_at + ttl_seconds) > ?",
                (key, now)
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None

    async def set_cache(self, key: str, value: dict, ttl_seconds: int = 86400):
        now = int(time.time())
        val_str = json.dumps(value)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO cache (key, value_json, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
                (key, val_str, now, ttl_seconds)
            )
            await db.commit()

    async def can_call(self) -> bool:
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT SUM(count) FROM llm_usage WHERE day = ?", (today,)
            ) as cursor:
                row = await cursor.fetchone()
                total = row[0] or 0
                return total < self.max_daily_calls

    async def record_call(self, model: str):
        today = date.today().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO llm_usage (day, model, count) VALUES (?, ?, 1)
                ON CONFLICT(day, model) DO UPDATE SET count = count + 1
                """,
                (today, model)
            )
            await db.commit()
```

## Checklist before finishing
- [ ] Schema migration script creates `cache`, `llm_usage`, `runs`, and `scrape_log` tables with required indexes.
- [ ] 24-hour TTL logic implemented and validated.
- [ ] Cache keys follow `scrape:{platform}:{normalized_query}` and `social:{source}:{normalized_query}`.
- [ ] `can_call()`, `record_call()`, and `remaining_today()` methods implemented using local date.
- [ ] `scripts/inspect_db.py` runs without error and correctly reports counts and usage.
