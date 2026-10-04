from backend.app.config import get_settings
from backend.app.schemas import SocialSignal


async def scrape_instagram_best_effort(queries: list[str]) -> tuple[str, list[SocialSignal]]:
    """
    Best-effort scraper for Instagram.
    Disabled by default via ENABLE_INSTAGRAM. Never bypasses logins or solves walls.
    """
    settings = get_settings()
    if not settings.ENABLE_INSTAGRAM:
        return "skipped", []

    # If enabled, returns skipped on login wall without credentials
    return "skipped", []
