import asyncio
import time
from typing import Union

from backend.app.schemas import NodeEvent, NodeId, NodeStatus, SSEEvent

AnySSEEvent = Union[SSEEvent, NodeEvent]


class EventManager:
    """Manages SSE event queues, monotonic seq numbers, node snapshots, and history replays per run."""

    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._history: dict[str, list[AnySSEEvent]] = {}
        self._seq_counters: dict[str, int] = {}
        self._node_snapshots: dict[str, dict[str, dict]] = {}
        self._active_connections: int = 0
        self._lock = asyncio.Lock()

    @property
    def active_connections(self) -> int:
        return self._active_connections

    def increment_connections(self) -> None:
        self._active_connections += 1

    def decrement_connections(self) -> None:
        self._active_connections = max(0, self._active_connections - 1)

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

    def _next_seq(self, run_id: str) -> int:
        current = self._seq_counters.get(run_id, 0)
        self._seq_counters[run_id] = current + 1
        return current

    def get_history(self, run_id: str, since_seq: int = -1) -> list[AnySSEEvent]:
        history = list(self._history.get(run_id, []))
        if since_seq >= 0:
            return [e for e in history if e.seq > since_seq]
        return history

    def get_node_snapshot(self, run_id: str) -> dict[str, dict]:
        return dict(self._node_snapshots.get(run_id, {}))

    async def emit_node(
        self,
        run_id: str,
        node_id: NodeId,
        status: NodeStatus,
        detail: str | None = None,
        metrics: dict[str, str | int | float] | None = None,
    ) -> NodeEvent:
        async with self._lock:
            seq = self._next_seq(run_id)
            event = NodeEvent(
                type="node",
                seq=seq,
                node_id=node_id,
                status=status,
                detail=detail,
                metrics=metrics,
                ts=time.time(),
            )

            if run_id not in self._history:
                self._history[run_id] = []
            self._history[run_id].append(event)

            if run_id not in self._node_snapshots:
                self._node_snapshots[run_id] = {}
            self._node_snapshots[run_id][node_id] = {
                "status": status,
                "detail": detail,
                "metrics": metrics,
                "ts": event.ts,
            }

            queues = list(self._queues.get(run_id, []))

        for q in queues:
            await q.put(event)

        return event

    async def emit(
        self,
        run_id: str,
        event_type: str,
        stage: str,
        message: str,
        data: dict | None = None,
    ) -> SSEEvent:
        async with self._lock:
            seq = self._next_seq(run_id)
            event = SSEEvent(
                seq=seq,
                type=event_type,  # type: ignore
                stage=stage,  # type: ignore
                message=message,
                data=data,
                ts=time.time(),
            )

            if run_id not in self._history:
                self._history[run_id] = []
            self._history[run_id].append(event)
            queues = list(self._queues.get(run_id, []))

        for q in queues:
            await q.put(event)

        return event


event_manager = EventManager()
