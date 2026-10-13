import asyncio
import hmac
import json
import logging
import secrets
import time
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.events import event_manager
from backend.app.orchestrator import WorkflowOrchestrator
from backend.app.schemas import ChatRequest, ChatResponse, ProductBrief, RunResult
from backend.app.security import limiter

logger = logging.getLogger("backend.routers.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])

# In-memory stores
active_ip_runs: dict[str, str] = {}  # ip -> run_id
active_run_tasks: dict[str, asyncio.Task] = {}  # run_id -> asyncio.Task
chat_histories: dict[str, list[dict[str, str]]] = {}  # run_id -> message history
run_tokens: dict[str, str] = {}  # run_id -> token
orchestrator_instance = WorkflowOrchestrator()


async def verify_run_token(run_id: str, x_run_token: str | None) -> str:
    """Verifies X-Run-Token header matches run_token using constant-time comparison."""
    if not x_run_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    expected_token = run_tokens.get(run_id)
    if not expected_token:
        async with get_db() as conn:
            async with conn.execute("SELECT run_token FROM runs WHERE id = ?", (run_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row["run_token"]:
                    expected_token = row["run_token"]
                    run_tokens[run_id] = expected_token

    if not expected_token or not hmac.compare_digest(x_run_token, expected_token):
        raise HTTPException(status_code=403, detail="Forbidden")

    return x_run_token


@router.post("", status_code=201)
@limiter.limit("5/minute")
async def create_run(brief: ProductBrief, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Enforce 1 active run per client IP
    if client_ip in active_ip_runs:
        existing_run = active_ip_runs[client_ip]
        async with get_db() as conn:
            async with conn.execute(
                "SELECT status FROM runs WHERE id = ?", (existing_run,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row["status"] in ("running", "pending"):
                    raise HTTPException(
                        status_code=429,
                        detail="A keyword analysis run is already in progress for your IP address.",
                    )

    run_id = uuid4().hex
    run_token = secrets.token_urlsafe(32)
    run_tokens[run_id] = run_token
    active_ip_runs[client_ip] = run_id
    chat_histories[run_id] = []

    # Insert initial run record with run_token
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO runs (id, brief_json, status, result_json, created_at, run_token)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, brief.model_dump_json(), "running", None, time.time(), run_token),
        )
        # Cap stored runs to 20: delete oldest
        await conn.execute(
            """
            DELETE FROM runs WHERE id NOT IN (
                SELECT id FROM runs ORDER BY created_at DESC LIMIT 20
            )
            """
        )
        await conn.commit()

    # Emit initial queued/skipped node states from registry
    from backend.app.scrapers.registry import load_registry
    registry = load_registry()
    settings = get_settings()

    await event_manager.emit_node(run_id, "brief", "success", f"{brief.color} {brief.tshirt_type}")
    await event_manager.emit_node(run_id, "planner", "queued")
    await event_manager.emit_node(run_id, "target_market", "queued")
    await event_manager.emit_node(run_id, "search_queries", "queued")
    await event_manager.emit_node(run_id, "marketplace", "queued")
    await event_manager.emit_node(run_id, "social", "queued")

    active_research = set(brief.research_sources or ["google", "pinterest", "reddit"])
    if settings.ENABLE_X:
        active_research.add("x")
    if settings.ENABLE_INSTAGRAM:
        active_research.add("instagram")

    for src in registry.sources:
        if src.kind in ("marketplace", "b2b", "quickcommerce"):
            if src.id in brief.platforms:
                await event_manager.emit_node(run_id, src.id, "queued")
            else:
                await event_manager.emit_node(run_id, src.id, "skipped", "Not requested")
        elif src.kind in ("search", "social"):
            if src.id in active_research:
                await event_manager.emit_node(run_id, src.id, "queued")
            else:
                await event_manager.emit_node(run_id, src.id, "skipped", "Not requested")

    await event_manager.emit_node(run_id, "analyst", "queued")
    await event_manager.emit_node(run_id, "output", "queued")

    async def emit_helper(event_type: str, stage: str, message: str, data: dict | None = None):
        await event_manager.emit(run_id, event_type, stage, message, data)

    async def emit_node_helper(node_id: str, status: str, detail: str | None = None, metrics: dict | None = None):
        await event_manager.emit_node(run_id, node_id, status, detail, metrics)  # type: ignore

    async def pipeline_wrapper():
        try:
            await orchestrator_instance.run_pipeline(run_id, brief, emit_helper, emit_node_helper)
        except asyncio.CancelledError:
            logger.info(f"Pipeline task for run {run_id} was cancelled.")
        finally:
            if active_ip_runs.get(client_ip) == run_id:
                del active_ip_runs[client_ip]
            if run_id in active_run_tasks:
                del active_run_tasks[run_id]

    task = asyncio.create_task(pipeline_wrapper())
    active_run_tasks[run_id] = task

    return {"run_id": run_id, "run_token": run_token}


@router.post("/{run_id}/cancel")
@limiter.limit("10/minute")
async def cancel_run(
    run_id: str,
    request: Request,
    x_run_token: str | None = Header(None, alias="X-Run-Token"),
):
    await verify_run_token(run_id, x_run_token)

    # Cancel asyncio task if running
    task = active_run_tasks.get(run_id)
    if task and not task.done():
        task.cancel()

    # Update database record
    async with get_db() as conn:
        await conn.execute("UPDATE runs SET status = ? WHERE id = ?", ("cancelled", run_id))
        await conn.commit()

    # Mark all currently running / queued nodes as skipped with detail "cancelled"
    snapshots = event_manager.get_node_snapshot(run_id)
    for node_id, snap in snapshots.items():
        if snap.get("status") in ("running", "queued"):
            await event_manager.emit_node(run_id, node_id, "skipped", "cancelled")  # type: ignore

    # Emit error-free done with cancelled=true
    await event_manager.emit(
        run_id,
        "done",
        "system",
        "Run was cancelled by user.",
        {"cancelled": True},
    )

    return {"run_id": run_id, "cancelled": True}


@router.get("/{run_id}/events")
async def stream_events(
    run_id: str,
    request: Request,
    x_run_token: str | None = Header(None, alias="X-Run-Token"),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
):
    await verify_run_token(run_id, x_run_token)

    # Cap: 10 concurrent SSE connections total
    if event_manager.active_connections >= 10:
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent event streams. Please wait for an existing stream to finish.",
        )

    queue = await event_manager.get_or_create_queue(run_id)
    since_seq = -1
    if last_event_id:
        try:
            since_seq = int(last_event_id)
        except ValueError:
            pass

    history = event_manager.get_history(run_id, since_seq=since_seq)
    event_manager.increment_connections()

    async def event_generator():
        try:
            # 1. Replay past events
            for past_event in history:
                yield {
                    "event": "message",
                    "id": str(past_event.seq),
                    "data": past_event.model_dump_json(),
                }
                if past_event.type in ("done", "error"):
                    return

            # 2. Stream live events
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": "message",
                        "id": str(event.seq),
                        "data": event.model_dump_json(),
                    }
                    if event.type in ("done", "error"):
                        break
                except TimeoutError:
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            event_manager.decrement_connections()
            await event_manager.remove_queue(run_id, queue)

    return EventSourceResponse(
        event_generator(),
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}")
async def get_run(run_id: str, x_run_token: str | None = Header(None, alias="X-Run-Token")):
    await verify_run_token(run_id, x_run_token)

    async with get_db() as conn:
        async with conn.execute(
            "SELECT status, result_json FROM runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Run not found.")

            status = row["status"]
            result_json = row["result_json"]
            nodes_snapshot = event_manager.get_node_snapshot(run_id)

            if status == "completed" and result_json:
                data = json.loads(result_json)
                data["nodes_snapshot"] = nodes_snapshot
                return RunResult.model_validate(data)

            return {
                "run_id": run_id,
                "status": status,
                "nodes_snapshot": nodes_snapshot,
            }


@router.post("/{run_id}/chat")
@limiter.limit("20/minute")
async def chat_with_analyst(
    run_id: str,
    chat_req: ChatRequest,
    request: Request,
    x_run_token: str | None = Header(None, alias="X-Run-Token"),
):
    await verify_run_token(run_id, x_run_token)

    async with get_db() as conn:
        async with conn.execute(
            "SELECT status, result_json FROM runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or not row["result_json"]:
                raise HTTPException(status_code=404, detail="Run not ready or not found for chat.")
            current_result = RunResult.model_validate(json.loads(row["result_json"]))

    history = chat_histories.get(run_id, [])

    response: ChatResponse = await orchestrator_instance.analyst.chat(
        current_result=current_result, message=chat_req.message, history=history
    )

    # Record message and reply in history
    history.append({"role": "user", "content": chat_req.message})
    history.append({"role": "assistant", "content": response.reply})
    chat_histories[run_id] = history

    # If platform patch returned, update in-memory and database result
    if response.patch:
        patch_map = {p.platform: p for p in response.patch}
        for i, plat in enumerate(current_result.platforms):
            if plat.platform in patch_map:
                current_result.platforms[i] = patch_map[plat.platform]

        async with get_db() as conn:
            await conn.execute(
                "UPDATE runs SET result_json = ? WHERE id = ?",
                (current_result.model_dump_json(), run_id),
            )
            await conn.commit()

    return response
