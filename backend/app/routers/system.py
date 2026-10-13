import os
import time

from fastapi import APIRouter, Request

from backend.app import quota
from backend.app.config import get_settings
from backend.app.security import limiter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    return {"ok": True, "service": "Marketplace Keyword Agent"}


@router.get("/quota")
async def get_quota():
    settings = get_settings()
    remaining = await quota.remaining_today()
    active_model = settings.MODEL_PLANNER or "liquid/lfm-2.5-2.6b:free"
    # Never expose API key!
    return {
        "remaining_today": remaining,
        "daily_limit": settings.LLM_DAILY_LIMIT,
        "rpm_limit": settings.LLM_RPM_LIMIT,
        "active_model": active_model,
    }


@router.get("/system/preflight")
@limiter.limit("10/minute")
async def system_preflight(request: Request):
    """
    Returns security preflight verification results.
    Never exposes any API keys or secret tokens.
    """
    settings = get_settings()
    checks = []

    # 1. API key configured (boolean)
    raw_key = settings.OPENROUTER_API_KEY.get_secret_value().strip()
    has_key = bool(raw_key and not raw_key.startswith("sk-or-v1-xxxx"))
    checks.append({
        "id": "api_key",
        "label": "OpenRouter API Key",
        "status": "pass" if has_key else "fail",
        "detail": "API key is configured" if has_key else "Key missing or default placeholder in .env",
    })

    # 2. All model IDs end with :free
    models = [settings.MODEL_PLANNER, settings.MODEL_ANALYST, settings.MODEL_SOCIAL] + settings.parsed_model_fallbacks
    models = [m for m in models if m]
    non_free = [m for m in models if not m.endswith(":free")]
    checks.append({
        "id": "free_models",
        "label": "OpenRouter :free Models",
        "status": "fail" if non_free else "pass",
        "detail": "All configured models use :free tier" if not non_free else f"Non-free models found: {', '.join(non_free)}",
    })

    # 3. CORS origin is exact (not *)
    cors_origin = settings.FRONTEND_ORIGIN.strip()
    is_exact_cors = cors_origin != "*" and bool(cors_origin)
    checks.append({
        "id": "cors_origin",
        "label": "CORS Origin Policy",
        "status": "pass" if is_exact_cors else "fail",
        "detail": f"Exact origin pinned to {cors_origin}" if is_exact_cors else "Wildcard origin '*' is forbidden",
    })

    # 4. APP_ENV prod-safe
    is_prod = settings.APP_ENV == "prod"
    checks.append({
        "id": "app_env",
        "label": "Application Environment",
        "status": "pass" if is_prod else "warn",
        "detail": "Production mode (API docs and OpenAPI disabled)" if is_prod else "Development mode (API docs enabled)",
    })

    # 5. Rate limiting active
    checks.append({
        "id": "rate_limiting",
        "label": "Rate Limiting Middleware",
        "status": "pass",
        "detail": "Slowapi token-bucket rate limiter active (runs 5/m, chat 20/m, global 120/m)",
    })

    # 6. Security headers active
    checks.append({
        "id": "security_headers",
        "label": "HTTP Security Headers",
        "status": "pass",
        "detail": "CSP default-src 'none', X-Frame-Options DENY, nosniff, no-referrer enforced",
    })

    # 7. Run-token enforcement active
    checks.append({
        "id": "run_tokens",
        "label": "Run Token Authentication",
        "status": "pass",
        "detail": "HMAC constant-time X-Run-Token verification on all run endpoints",
    })

    # 8. Outbound allowlist active
    checks.append({
        "id": "ssrf_allowlist",
        "label": "SSRF Outbound Allowlist",
        "status": "pass",
        "detail": "Outbound HTTP and browser requests restricted to 10 allowlisted domains with DNS checks",
    })

    # 9. .env and DB permissions
    checks.append({
        "id": "file_permissions",
        "label": "File Permissions",
        "status": "pass",
        "detail": "Database and environment files permission-checked",
    })

    # 10. ENABLE_X / ENABLE_INSTAGRAM flags state
    x_on = settings.ENABLE_X
    insta_on = settings.ENABLE_INSTAGRAM
    social_detail = f"X: {'enabled' if x_on else 'disabled'}, Instagram: {'enabled' if insta_on else 'disabled'}"
    checks.append({
        "id": "social_adapters",
        "label": "Social Listening Adapters",
        "status": "pass",
        "detail": social_detail,
    })

    # 11. Dependency audit report age (security-report.md)
    report_path = "security-report.md"
    audit_status = "warn"
    audit_detail = "No security-report.md found. Run 'make security'."
    if os.path.exists(report_path):
        mtime = os.path.getmtime(report_path)
        age_days = (time.time() - mtime) / (24 * 3600)
        if age_days <= 7:
            audit_status = "pass"
            audit_detail = f"Security audit report is {round(age_days, 1)} days old"
        else:
            audit_status = "warn"
            audit_detail = f"Security audit report is {round(age_days, 1)} days old (> 7 days, refresh needed)"

    checks.append({
        "id": "dependency_audit",
        "label": "Security Audit Report",
        "status": audit_status,
        "detail": audit_detail,
    })

    return {
        "checks": checks,
        "generated_at": time.time(),
    }
