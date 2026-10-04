import asyncio
import time

from backend.app.schemas import SSEEvent


class EventManager:
    """Manages SSE event queues and history replays per run."""

    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._history: dict[str, list[SSEEvent]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_queue(self, run_id: str) -> asyncio.Queue:
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue()
            if run_id not in self._queues:
                self._queues[run_id] = []
            self._queues[run_id].append(q)
            return q

    async def remove_queue(self, run_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if run_id in self._queues and queue in self._queues[run_id]:
                self._queues[run_id].remove(queue)
                if not self._queues[run_id]:
                    del self._queues[run_id]

    def get_history(self, run_id: str) -> list[SSEEvent]:
        return list(self._history.get(run_id, []))

    async def emit(
        self, run_id: str, event_type: str, stage: str, message: str, data: dict | None = None
    ) -> None:
        event = SSEEvent(type=event_type, stage=stage, message=message, data=data, ts=time.time())

        async with self._lock:
            if run_id not in self._history:
                self._history[run_id] = []
            self._history[run_id].append(event)
            queues = list(self._queues.get(run_id, []))

        for q in queues:
            await q.put(event)


event_manager = EventManager()
