import json
import logging
import os
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from pydantic import ValidationError

from backend.app.agents.analyst import gate_keywords
from backend.app.config import get_settings
from backend.app.db import init_db
from backend.app.main import app
from backend.app.net.safe_http import SSRFError, validate_url
from backend.app.schemas import ProductBrief
from backend.app.security import RedactingFilter

TEST_DB_PATH = "backend/data/test_security.db"


@pytest_asyncio.fixture(autouse=True)
async def setup_security_test(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "DATABASE_PATH", TEST_DB_PATH)
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass
    await init_db(TEST_DB_PATH)
    yield
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_security_headers_present_on_response():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert "camera=()" in headers.get("Permissions-Policy", "")
        assert headers.get("Cache-Control") == "no-store"
        assert "default-src 'none'" in headers.get("Content-Security-Policy", "")


@pytest.mark.asyncio
async def test_cors_rejects_unknown_origin():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Preflight from malicious origin
        resp = await client.options(
            "/api/health",
            headers={
                "Origin": "http://evil-attacker.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "http://evil-attacker.com"
        assert resp.headers.get("access-control-allow-origin") != "*"


@pytest.mark.asyncio
async def test_body_over_64kb_returns_413():
    huge_payload = {"platforms": ["amazon"], "tshirt_type": "x" * 70000, "color": "black"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/runs", json=huge_payload)
        assert resp.status_code == 413
        assert "payload_too_large" in resp.text


@pytest.mark.asyncio
async def test_token_enforcement_returns_403():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        fake_run_id = "nonexistent_run_123"
        # 1. get run without token
        resp1 = await client.get(f"/api/runs/{fake_run_id}")
        assert resp1.status_code == 403

        # 2. cancel without token
        resp2 = await client.post(f"/api/runs/{fake_run_id}/cancel")
        assert resp2.status_code == 403

        # 3. chat without token
        resp3 = await client.post(
            f"/api/runs/{fake_run_id}/chat", json={"message": "hello"}
        )
        assert resp3.status_code == 403

        # 4. events without token
        resp4 = await client.get(f"/api/runs/{fake_run_id}/events")
        assert resp4.status_code == 403


@pytest.mark.asyncio
async def test_brief_validation_rejects_malicious_inputs():
    # 1. Rejects <script> tags
    with pytest.raises(ValidationError):
        ProductBrief(
            platforms=["amazon"],
            tshirt_type="<script>alert(1)</script>",
            color="black",
        )

    # 2. Rejects URL schemes
    with pytest.raises(ValidationError):
        ProductBrief(
            platforms=["amazon"],
            tshirt_type="oversized tee",
            color="black",
            extra_details="check out https://evil.com/drop",
        )

    # 3. Rejects control characters
    with pytest.raises(ValidationError):
        ProductBrief(
            platforms=["amazon"],
            tshirt_type="\x00\x01\x02bad\x03",
            color="black",
        )

    # 4. Rejects invalid price range (min > max)
    with pytest.raises(ValidationError):
        ProductBrief(
            platforms=["amazon"],
            tshirt_type="oversized tee",
            color="black",
            price_min=1000,
            price_max=500,
        )


@pytest.mark.asyncio
async def test_ssrf_safe_http_validation():
    # 1. Rejects non-allowlisted host
    with pytest.raises(SSRFError, match="not in the outbound allowlist"):
        validate_url("https://evil-internal-service.com/api")

    # 2. Rejects non-https
    with pytest.raises(SSRFError, match="Only https is permitted"):
        validate_url("http://amazon.in/dp/123")

    # 3. Rejects file: or javascript: schemes
    with pytest.raises(SSRFError):
        validate_url("file:///etc/passwd")

    # 4. Valid host passes validation
    validate_url("https://www.amazon.in/s?k=tshirt")


@pytest.mark.asyncio
async def test_prompt_injection_gate_keywords_fixture():
    fixtures_path = Path(__file__).parent / "injection-payloads.json"
    with open(fixtures_path, encoding="utf-8") as f:
        payloads = json.load(f)

    cleaned = gate_keywords(payloads, max_count=25)
    # Ensure no instruction-like, url, or html payloads survived
    for kw in cleaned:
        assert "<" not in kw
        assert ">" not in kw
        assert "http" not in kw
        assert "ignore" not in kw
        assert "system prompt" not in kw
        assert "@" not in kw
        assert "eval" not in kw

    # Safe keywords survived
    assert "oversized cotton t shirt" in cleaned
    assert "black streetwear tee" in cleaned
    assert "relaxed fit round neck" in cleaned


def test_log_redaction_filter():
    filter_ = RedactingFilter()
    secret_key = "sk-or-v1-abcdef0123456789abcdef0123456789"
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Calling OpenRouter with key {secret_key}",
        args=(),
        exc_info=None,
    )
    filter_.filter(record)
    assert secret_key not in record.msg
    assert "sk-or-[REDACTED]" in record.msg


@pytest.mark.asyncio
async def test_no_api_response_leaks_key():
    settings = get_settings()
    raw_key = settings.OPENROUTER_API_KEY.get_secret_value()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Check quota
        q_resp = await client.get("/api/quota")
        assert raw_key not in q_resp.text

        # Check preflight
        p_resp = await client.get("/api/system/preflight")
        assert raw_key not in p_resp.text
        assert p_resp.json()["checks"][0]["id"] == "api_key"
        assert "sk-" not in p_resp.text


@pytest.mark.asyncio
async def test_docs_disabled_in_prod(monkeypatch):
    # Set APP_ENV to prod
    from backend.app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "prod")

    # In prod, OpenAPI docs routes are set to None
    from fastapi import FastAPI
    prod_app = FastAPI(
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prod_app), base_url="http://test"
    ) as client:
        d_resp = await client.get("/docs")
        assert d_resp.status_code == 404
        o_resp = await client.get("/openapi.json")
        assert o_resp.status_code == 404
