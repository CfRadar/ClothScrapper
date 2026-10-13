import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        import uvicorn.loops.asyncio
        import uvicorn.loops.auto

        uvicorn.loops.auto.loop_factory = lambda use_subprocess=False: asyncio.ProactorEventLoop
        uvicorn.loops.asyncio.asyncio_loop_factory = (
            lambda use_subprocess=False: asyncio.ProactorEventLoop
        )
    except ImportError:
        pass

from fastapi import FastAPI

from backend.app.config import get_settings
from backend.app.db import init_db
from backend.app.routers import runs, sources, system
from backend.app.scrapers.browser import BrowserManager
from backend.app.security import setup_security

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database schema...")
    await init_db()
    from backend.app.scrapers.health import reset_circuit_breaker
    await reset_circuit_breaker()
    yield
    # Teardown
    logger.info("Closing browser manager...")
    await BrowserManager.get_instance().close()


settings = get_settings()
is_prod = settings.APP_ENV == "prod"

app = FastAPI(
    title="Marketplace Keyword Agent",
    description="Multi-agent search keyword intelligence for Indian marketplaces",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=None if is_prod else "/openapi.json",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
)

# Apply security middlewares: headers, body limit, trusted host, strict CORS, slowapi limiter
setup_security(app)

app.include_router(system.router)
app.include_router(sources.router)
app.include_router(runs.router)
