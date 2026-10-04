from backend.app.config import get_settings
from backend.app.schemas import SocialSignal


async def scrape_x_best_effort(queries: list[str]) -> tuple[str, list[SocialSignal]]:
    """
    Best-effort scraper for X (Twitter).
    Disabled by default via ENABLE_X. Never bypasses logins or solves walls.
    """
    settings = get_settings()
    if not settings.ENABLE_X:
        return "skipped", []

    # If enabled, returns skipped on login wall without credentials
    return "skipped", []
