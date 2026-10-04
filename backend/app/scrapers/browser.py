import asyncio
import logging
import os
import random
from typing import Optional

import yaml
from backend.app.config import get_settings
from playwright.async_api import Browser, BrowserContext, Page, Playwright, Route, async_playwright

logger = logging.getLogger("backend.scrapers.browser")

SELECTORS_PATH = os.path.join(os.path.dirname(__file__), "selectors.yaml")


def load_selectors() -> dict:
    if os.path.exists(SELECTORS_PATH):
        with open(SELECTORS_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


class BrowserManager:
    """
    Singleton manager for Playwright Chromium.
    Maintains one isolated BrowserContext per platform with polite Indian locale settings.
    """

    _instance: Optional["BrowserManager"] = None

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._selectors: dict = load_selectors()
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        if cls._instance is None:
            cls._instance = BrowserManager()
        return cls._instance

    async def _ensure_browser(self) -> Browser:
        if self._browser is None:
            async with self._lock:
                if self._browser is None:
                    logger.info("Launching Playwright Chromium headless...")
                    self._playwright = await async_playwright().start()
                    launch_kwargs = {
                        "headless": True,
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                        ],
                    }
                    try:
                        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
                    except Exception as launch_err:
                        logger.warning(
                            f"Bundled Chromium launch failed ({launch_err}). Falling back to system 'msedge' channel."
                        )
                        try:
                            self._browser = await self._playwright.chromium.launch(
                                channel="msedge", **launch_kwargs
                            )
                        except Exception:
                            self._browser = await self._playwright.chromium.launch(
                                channel="chrome", **launch_kwargs
                            )
        return self._browser

    async def get_context(self, platform: str) -> BrowserContext:
        """Get or create isolated browser context for a platform."""
        await self._ensure_browser()
        if platform not in self._contexts or self._contexts[platform].pages == []:
            context = await self._browser.new_context(
                viewport={"width": 1366, "height": 900},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            )
            self._contexts[platform] = context
        return self._contexts[platform]

    async def polite_goto(
        self, page: Page, url: str, platform: str, timeout_ms: int = 30000
    ) -> tuple[bool, str]:
        """
        Navigates politely with route abortion of heavy media, random delay,
        and automated block/CAPTCHA detection.
        Returns (is_blocked: bool, page_content: str).
        """
        settings = get_settings()

        # Abort images, fonts, media to optimize bandwidth and speed
        async def route_handler(route: Route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

        # Polite jitter delay
        delay = random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX)
        await asyncio.sleep(delay)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        except Exception as e:
            logger.warning(f"Navigation error for {url}: {e}")

        # Check for CAPTCHA / bot challenges
        content = await page.content()
        is_blocked = self.detect_block(platform, page.url, content)
        return is_blocked, content

    def detect_block(self, platform: str, current_url: str, content: str) -> bool:
        """Check if platform served a robot check, CAPTCHA, or access denied page."""
        captcha_tokens = self._selectors.get(platform, {}).get("captcha_identifiers", [])
        lower_content = content.lower()
        lower_url = current_url.lower()

        for token in captcha_tokens:
            token_lower = token.lower()
            if token_lower in lower_content or token_lower in lower_url:
                logger.warning(f"Detected bot check on {platform}: '{token}'")
                return True
        return False

    async def close(self) -> None:
        """Gracefully close all contexts and the browser instance."""
        async with self._lock:
            for ctx in self._contexts.values():
                try:
                    await ctx.close()
                except Exception:
                    pass
            self._contexts.clear()

            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            logger.info("Playwright browser closed.")
