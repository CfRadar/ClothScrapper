import os
import time

import pytest
import pytest_asyncio
from backend.app import cache, quota
from backend.app.db import init_db

TEST_DB_PATH = "backend/data/test_app.db"


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    await init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.mark.asyncio
async def test_cache_set_and_get():
    key = "scrape:amazon:mens_cotton_tee"
    data = {"products": [{"title": "Oversized Tee", "price": 499}]}

    # Initially empty
    assert await cache.get(key, db_path=TEST_DB_PATH) is None

    # Set cache with 10s TTL
    await cache.set(key, data, ttl=10, db_path=TEST_DB_PATH)
    cached = await cache.get(key, db_path=TEST_DB_PATH)
    assert cached == data
    assert cached["products"][0]["title"] == "Oversized Tee"


@pytest.mark.asyncio
async def test_cache_expiration():
    key = "scrape:myntra:black_tee"
    data = {"items": ["item1"]}

    # Set with 1s TTL
    await cache.set(key, data, ttl=1, db_path=TEST_DB_PATH)
    assert await cache.get(key, db_path=TEST_DB_PATH) == data

    # Wait for expiration
    time.sleep(1.2)
    assert await cache.get(key, db_path=TEST_DB_PATH) is None


@pytest.mark.asyncio
async def test_quota_tracking(monkeypatch):
    # Set limit to 5
    from backend.app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "LLM_DAILY_LIMIT", 5)

    assert await quota.can_call(db_path=TEST_DB_PATH) is True
    assert await quota.remaining_today(db_path=TEST_DB_PATH) == 5

    # Record 3 calls
    await quota.record("google/gemini-2.0-flash-exp:free", db_path=TEST_DB_PATH)
    await quota.record("google/gemini-2.0-flash-exp:free", db_path=TEST_DB_PATH)
    await quota.record("meta-llama/llama-3.3-70b-instruct:free", db_path=TEST_DB_PATH)

    assert await quota.get_today_used(db_path=TEST_DB_PATH) == 3
    assert await quota.remaining_today(db_path=TEST_DB_PATH) == 2
    assert await quota.can_call(db_path=TEST_DB_PATH) is True

    # Record 2 more calls to reach cap
    await quota.record("google/gemini-2.0-flash-exp:free", db_path=TEST_DB_PATH)
    await quota.record("google/gemini-2.0-flash-exp:free", db_path=TEST_DB_PATH)

    assert await quota.remaining_today(db_path=TEST_DB_PATH) == 0
    assert await quota.can_call(db_path=TEST_DB_PATH) is False
