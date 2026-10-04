import asyncio
import json
import logging
import time
from uuid import uuid4

from backend.app.db import get_db
from backend.app.events import event_manager
from backend.app.orchestrator import WorkflowOrchestrator
from backend.app.schemas import ChatRequest, ChatResponse, ProductBrief, RunResult, SSEEvent
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger("backend.routers.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])

# In-memory stores
active_ip_runs: dict[str, str] = {}  # ip -> run_id
chat_histories: dict[str, list[dict[str, str]]] = {}  # run_id -> message history
orchestrator_instance = WorkflowOrchestrator()


@router.post("", status_code=201)
async def create_run(brief: ProductBrief, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Enforce simple per-IP guard: max 1 concurrent run per client
    if client_ip in active_ip_runs:
        existing_run = active_ip_runs[client_ip]
        # Check if existing run is still active
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
    active_ip_runs[client_ip] = run_id
    chat_histories[run_id] = []

    # Insert initial run record immediately so it exists before async dispatch
    async with get_db() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO runs (id, brief_json, status, result_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, brief.model_dump_json(), "running", None, time.time()),
        )
        await conn.commit()

    async def emit_helper(event_type: str, stage: str, message: str, data: dict | None = None):
        await event_manager.emit(run_id, event_type, stage, message, data)

    async def pipeline_wrapper():
        try:
            await orchestrator_instance.run_pipeline(run_id, brief, emit_helper)
        finally:
            if active_ip_runs.get(client_ip) == run_id:
                del active_ip_runs[client_ip]

    asyncio.create_task(pipeline_wrapper())
    return {"run_id": run_id}


@router.get("/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    queue = await event_manager.get_or_create_queue(run_id)
    history = event_manager.get_history(run_id)

    async def event_generator():
        try:
            # 1. Replay past events
            for past_event in history:
                yield {"event": "message", "data": past_event.model_dump_json()}
                if past_event.type in ("done", "error"):
                    return

            # 2. Stream live events
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event: SSEEvent = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"event": "message", "data": event.model_dump_json()}
                    if event.type in ("done", "error"):
                        break
                except TimeoutError:
                    # Keepalive comment to prevent proxy timeout
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            await event_manager.remove_queue(run_id, queue)

    return EventSourceResponse(
        event_generator(),
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}")
async def get_run(run_id: str):
    async with get_db() as conn:
        async with conn.execute(
            "SELECT status, result_json FROM runs WHERE id = ?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Run not found.")

            status = row["status"]
            result_json = row["result_json"]

            if status == "completed" and result_json:
                data = json.loads(result_json)
                return RunResult.model_validate(data)
            return {"run_id": run_id, "status": status}


@router.post("/{run_id}/chat")
async def chat_with_analyst(run_id: str, chat_req: ChatRequest):
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

    # If keyword patch returned, update in-memory and database result
    if response.keywords_patch:
        patch_map = {p.platform: p.keywords for p in response.keywords_patch}
        for kw_item in current_result.keywords:
            if kw_item.platform in patch_map:
                kw_item.keywords = patch_map[kw_item.platform]

        async with get_db() as conn:
            await conn.execute(
                "UPDATE runs SET result_json = ? WHERE id = ?",
                (current_result.model_dump_json(), run_id),
            )
            await conn.commit()

    return response
