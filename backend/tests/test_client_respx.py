import os

import httpx
import pytest
import pytest_asyncio
import respx
from backend.app import quota
from backend.app.config import Settings
from backend.app.db import init_db
from backend.app.llm.client import OpenRouterClient, QuotaExceeded
from pydantic import BaseModel, SecretStr

TEST_DB_PATH = "backend/data/test_client.db"


class KeywordsOutput(BaseModel):
    keywords: list[str]


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    await init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def make_test_settings():
    return Settings(
        OPENROUTER_API_KEY=SecretStr("sk-or-test-key-12345"),
        MODEL_PLANNER="google/gemini-2.0-flash-exp:free",
        MODEL_FALLBACKS="meta-llama/llama-3.3-70b-instruct:free",
        DATABASE_PATH=TEST_DB_PATH,
        LLM_RPM_LIMIT=100,
    )


@pytest.mark.asyncio
@respx.mock
async def test_client_chat_success():
    settings = make_test_settings()
    client = OpenRouterClient(settings=settings)

    respx.post("https://openrouter.ai/api/v1/chat/completions").respond(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "content": '{"keywords": ["oversized black tee", "cotton drop shoulder"]}'
                    }
                }
            ]
        },
    )

    result = await client.chat(
        role="planner", system="Generate keywords", user="Black t-shirt", schema=KeywordsOutput
    )

    assert isinstance(result, KeywordsOutput)
    assert result.keywords == ["oversized black tee", "cotton drop shoulder"]
    assert client.llm_calls_used == 1


@pytest.mark.asyncio
@respx.mock
async def test_client_repair_flow():
    settings = make_test_settings()
    client = OpenRouterClient(settings=settings)

    route = respx.post("https://openrouter.ai/api/v1/chat/completions")
    # First response is invalid/prose, second is repaired JSON
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Sure! Here is the keyword: oversized tee"}}]
            },
        ),
        httpx.Response(
            200, json={"choices": [{"message": {"content": '{"keywords": ["oversized tee"]}'}}]}
        ),
    ]

    result = await client.chat(
        role="planner", system="Generate keywords", user="Tee", schema=KeywordsOutput
    )

    assert isinstance(result, KeywordsOutput)
    assert result.keywords == ["oversized tee"]
    assert client.llm_calls_used == 2


@pytest.mark.asyncio
@respx.mock
async def test_client_429_fallback_to_next_model():
    settings = make_test_settings()
    client = OpenRouterClient(settings=settings)

    route = respx.post("https://openrouter.ai/api/v1/chat/completions")
    # Primary model returns 429, fallback model returns 200
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "0.1"}),
        httpx.Response(
            200, json={"choices": [{"message": {"content": '{"keywords": ["fallback keyword"]}'}}]}
        ),
    ]

    result = await client.chat(role="planner", system="Generate", user="Tee", schema=KeywordsOutput)

    assert isinstance(result, KeywordsOutput)
    assert result.keywords == ["fallback keyword"]


@pytest.mark.asyncio
async def test_client_quota_exceeded_blocks_call(monkeypatch):
    settings = make_test_settings()
    settings.LLM_DAILY_LIMIT = 1
    client = OpenRouterClient(settings=settings)

    # Exhaust quota in test db
    await quota.record("google/gemini-2.0-flash-exp:free", db_path=TEST_DB_PATH)
    assert await quota.can_call(db_path=TEST_DB_PATH, daily_limit=settings.LLM_DAILY_LIMIT) is False

    with pytest.raises(QuotaExceeded):
        await client.chat(role="planner", system="s", user="u", schema=KeywordsOutput)
