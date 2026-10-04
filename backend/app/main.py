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

from backend.app.config import get_settings
from backend.app.db import init_db
from backend.app.routers import runs, system
from backend.app.scrapers.browser import BrowserManager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database schema...")
    await init_db()
    yield
    # Teardown
    logger.info("Closing browser manager...")
    await BrowserManager.get_instance().close()


app = FastAPI(
    title="Marketplace Keyword Agent",
    description="Multi-agent search keyword intelligence for Indian marketplaces",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(runs.router)
