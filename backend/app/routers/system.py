from backend.app import quota
from backend.app.config import get_settings
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    return {"ok": True, "service": "Marketplace Keyword Agent"}


@router.get("/quota")
async def get_quota():
    settings = get_settings()
    remaining = await quota.remaining_today()
    active_model = settings.MODEL_PLANNER or "google/gemini-2.0-flash-exp:free"
    # Never expose API key!
    return {
        "remaining_today": remaining,
        "daily_limit": settings.LLM_DAILY_LIMIT,
        "rpm_limit": settings.LLM_RPM_LIMIT,
        "active_model": active_model,
    }
