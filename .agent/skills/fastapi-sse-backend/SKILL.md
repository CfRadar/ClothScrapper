---
name: fastapi-sse-backend
description: Guides FastAPI backend architecture, async SSE streaming, Pydantic v2 validation, lifespan lifecycle management, and secure quota APIs. Use when building or refactoring FastAPI endpoints, background run managers, Server-Sent Event feeds, or health and quota endpoints.
---

# FastAPI SSE Backend

## Purpose
This skill establishes the backend application structure using FastAPI, Pydantic v2, and Server-Sent Events (SSE). It details async non-blocking concurrency, lifespan startup/teardown handlers for SQLite and Playwright, strict configuration hygiene with `pydantic-settings`, real-time progress streaming to the React frontend, and secure quota and health endpoints.

## When to use
- When setting up or modifying FastAPI application routes and middleware.
- When implementing real-time progress streaming for run execution (`/api/runs/{run_id}/stream`).
- When defining Pydantic v2 request/response schemas.
- When managing application lifecycle events (database connection pool, Playwright browser instances).
- When configuring CORS for the local Vite development server (`http://localhost:5173`).

## Backend Project Layout
```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization, CORS, lifespan
│   ├── config.py            # Settings loaded via pydantic-settings
│   ├── models/              # Pydantic v2 schemas (requests, responses, events)
│   ├── routers/
│   │   ├── runs.py          # Start run, stream SSE, run details, chat
│   │   ├── quota.py         # Quota telemetry (/api/quota)
│   │   └── health.py        # Healthcheck endpoint (/api/health)
│   ├── services/
│   │   ├── orchestrator.py  # 4-agent asyncio pipeline orchestrator
│   │   ├── openrouter.py    # OpenRouter free client with rate limiter
│   │   ├── scrapers/        # Playwright & Reddit scrapers
│   │   ├── scoring.py       # Deterministic keyword scoring
│   │   └── database.py      # aiosqlite cache and quota manager
└── data/                    # SQLite database storage (app.db)
```

## Step-by-step procedure

1. **Configure Environment with `pydantic-settings`**:
   - Store all credentials and settings securely:
     ```python
     from pydantic_settings import BaseSettings
     from pydantic import SecretStr

     class Settings(BaseSettings):
         OPENROUTER_API_KEY: SecretStr
         OPENROUTER_PRIMARY_MODEL: str = "google/gemini-2.0-flash-exp:free"
         OPENROUTER_FALLBACK_MODELS: str = "meta-llama/llama-3.3-70b-instruct:free"
         DATABASE_PATH: str = "backend/data/app.db"
         CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
         ENABLE_X: bool = False
         ENABLE_INSTAGRAM: bool = False

         model_config = {"env_file": ".env", "extra": "ignore"}
     ```

2. **Lifespan Startup and Shutdown**:
   - Use `asynccontextmanager` to initialize SQLite tables and prepare Playwright:
     ```python
     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Startup: init DB tables
         await db.init_db()
         app.state.playwright_browser = None # Lazy load on first scrape to save memory
         yield
         # Teardown: close browser & db
         if app.state.playwright_browser:
             await app.state.playwright_browser.close()
     ```

3. **Standardize SSE Event Schema**:
   - Every event emitted over `/api/runs/{run_id}/stream` conforms to:
     ```python
     class SSEEvent(BaseModel):
         type: Literal["status", "progress", "partial", "complete", "error"]
         stage: Literal["planner", "marketplace", "social", "scoring", "analyst", "done"]
         message: str
         data: dict[str, Any] | None = None
         ts: float = Field(default_factory=time.time)

         def to_sse(self) -> str:
             return f"data: {self.model_dump_json()}\n\n"
     ```

4. **Implement Streaming Route (`StreamingResponse` / `asyncio.Queue`)**:
   - Each active run maintains an in-memory `asyncio.Queue` of `SSEEvent` objects.
   - Route handler yields from the queue until the completion event or client disconnect:
     ```python
     @router.get("/api/runs/{run_id}/stream")
     async def stream_run_events(run_id: str):
         queue = run_manager.get_queue(run_id)
         if not queue:
             raise HTTPException(status_code=404, detail="Run not found")

         async def event_generator():
             try:
                 while True:
                     event: SSEEvent = await queue.get()
                     yield event.to_sse()
                     if event.type in ("complete", "error"):
                         break
             except asyncio.CancelledError:
                 # Handle client disconnect gracefully
                 pass

         return StreamingResponse(
             event_generator(),
             media_type="text/event-stream",
             headers={
                 "Cache-Control": "no-cache",
                 "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"
             }
         )
     ```

5. **Expose Health & Quota Endpoints**:
   - `/api/health`: Returns service status and DB reachability.
   - `/api/quota`: Returns today's calls, remaining budget, and active model. **NEVER expose the API key.**
     ```json
     {
       "today_used": 12,
       "daily_limit": 150,
       "remaining": 138,
       "active_model": "google/gemini-2.0-flash-exp:free"
     }
     ```

6. **Handle Graceful Run Cancellation**:
   - Store running `asyncio.Task` references in an active task dictionary.
   - `/api/runs/{run_id}/cancel` triggers `task.cancel()`, updates `RunState.status = "cancelled"`, and notifies the frontend.

## Rules (do / don't)
- **DO** use non-blocking async operations (`aiosqlite`, `httpx`, `asyncio.sleep`) throughout the entire application.
- **DO** load all configuration through `pydantic-settings` using `SecretStr` for API credentials.
- **DO** include `X-Accel-Buffering: no` and `Cache-Control: no-cache` headers on SSE endpoints.
- **DON'T** call synchronous `requests`, synchronous `time.sleep()`, or synchronous `sqlite3` inside async routes.
- **DON'T** ever return the OpenRouter API key in any health, quota, or debugging API response.
- **DON'T** launch heavy Playwright browser instances eagerly at app launch; load lazily on first scrape.

## Examples

### Complete SSE Route with Keep-Alive Heartbeat
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter()

@router.get("/api/runs/{run_id}/stream")
async def run_stream(run_id: str):
    async def event_stream():
        queue = get_run_queue(run_id)
        while True:
            try:
                # Wait for next event with a 15-second timeout for keepalive
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {event.model_dump_json()}\n\n"
                if event.type in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                # Send comment ping to prevent proxy/browser timeout
                yield ": keepalive\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

## Checklist before finishing
- [ ] FastAPI lifespan configured for async startup and cleanup.
- [ ] Configuration loaded via `pydantic-settings` with `SecretStr` for API keys.
- [ ] CORS allows Vite development port (`http://localhost:5173`).
- [ ] SSE event schema contains `type`, `stage`, `message`, `data`, and `ts`.
- [ ] Keep-alive heartbeats and cancellation cleanup handled in SSE generator.
- [ ] `/api/health` and `/api/quota` endpoints implemented without leaking secrets.
