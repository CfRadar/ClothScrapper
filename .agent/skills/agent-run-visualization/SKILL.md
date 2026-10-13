---
name: agent-run-visualization
description: Governs the mapping of backend agent execution and Server-Sent Events (SSE) to frontend workflow node visual states, strict status state machines, edge animation rules, and idempotent event replay. Use when wiring SSE feeds into the workflow canvas.
---

# Agent Run Visualization

## Purpose
This skill defines the contract and synchronization mechanism between the backend multi-agent pipeline and the frontend workflow graph canvas. It specifies the 14-node registry, valid state machine transitions, the extended SSE event model, deterministic edge state derivation, and idempotent event reduction with replay handling.

## When to use
- When emitting node-level execution progress from backend agents.
- When handling SSE event streams in the React state store or reducer.
- When deriving visual states (active edges, completed paths, warning indicators) from node statuses.
- When testing the canvas with recorded or simulated execution scenarios.

## Node Registry
Every node in the canvas maps directly to a discrete pipeline checkpoint:
| Node ID | Type | Description |
|---|---|---|
| `brief` | Input | Seller brief submitted via form |
| `planner` | Agent 1 | AI Planner analyzing audience & queries |
| `target_market` | Data | Inferred demographics & shopping personas |
| `search_queries` | Data | Generated marketplace & social queries |
| `marketplace` | Agent 2 | Retail scraper coordinator gateway |
| `amazon` | Channel | Amazon.in search card & suggest scraping |
| `myntra` | Channel | Myntra catalog & state scraping |
| `flipkart` | Channel | Flipkart DOM & regex price parsing |
| `social` | Agent 3 | Social listener coordinator gateway |
| `reddit` | Channel | Reddit fashion subreddits public JSON |
| `x` | Channel | X (Twitter) public trend listening (best effort) |
| `instagram` | Channel | Instagram public hashtag listening (best effort) |
| `analyst` | Agent 4 | AI Analyst keyword scoring & factor synthesis |
| `output` | Output | Final keyword cards, factors, and chat ready |

## Status State Machine
Each node advances along strict unidirectional paths:
```
           +-----------+
           |   idle    |
           +-----+-----+
                 |
                 v
           +-----------+
           |  queued   |
           +-----+-----+
                 |
                 v
           +-----------+
    +----->|  running  |------+
    |      +-----+-----+      |
    |            |            |
    v            v            v
+---------+ +---------+ +-----------+
| success | | warning | |   error   |
+---------+ +---------+ +-----------+
     ^
     | (if disabled/pruned)
+----+----+
| skipped |
+---------+
```
- **Allowed Transitions**:
  - `idle -> queued -> running -> success`
  - `running -> warning` (e.g. partial results or robot challenge fallback)
  - `running -> error` (e.g. unhandled network/service failure)
  - `queued -> skipped` (e.g. channel disabled via environment flag like `ENABLE_X=false`)
- **Terminal States**: `success`, `warning`, `error`, and `skipped` are terminal for a given run and cannot be overwritten by earlier events.

## SSE Event Protocol
In addition to coarse `stage` and `progress` events, the backend emits granular `node` events:
```json
{
  "type": "node",
  "node_id": "amazon",
  "status": "running",
  "detail": "query 2/5 executing ('black oversized tee')",
  "metrics": {
    "queries_done": 2,
    "products_scraped": 42,
    "cache_hit": false,
    "duration_ms": 1420
  },
  "seq": 14,
  "ts": 1728045600.123
}
```

## Edge Status Derivation
Edge visual states are purely derived from their incident nodes:
- **`idle`**: Source node is `idle` or `queued`.
- **`active`**: Source node is `running` OR (`success`/`warning` AND target node is `queued`/`running`). Animates dashing motion.
- **`done`**: Source is `success`/`warning` AND target is `success`/`warning`/`done`. Solid accented stroke.
- **`error`**: Source or target is `error`. Solid danger stroke.
- **`skipped`**: Source or target is `skipped`. Faded dashed stroke.

## Step-by-step procedure

1. **Backend Helper Function (`emit_node`)**:
   - Provide a clean helper inside backend agent routines:
     ```python
     async def emit_node(
         emit: Callable,
         node_id: str,
         status: Literal["queued", "running", "success", "warning", "error", "skipped"],
         detail: str | None = None,
         metrics: dict[str, Any] | None = None,
     ) -> None:
         await emit(
             event_type="node",
             stage=map_node_to_stage(node_id),
             message=detail or f"Node {node_id} is {status}",
             data={
                 "node_id": node_id,
                 "status": status,
                 "detail": detail,
                 "metrics": metrics or {},
             },
         )
     ```

2. **Frontend Idempotent Reducer Pattern**:
   - Handle sequence ordering and ignore stale events:
     ```typescript
     export function workflowReducer(state: WorkflowState, event: SSEEvent): WorkflowState {
       if (event.type !== "node" || !event.data?.node_id) return state;

       const { node_id, status, detail, metrics } = event.data;
       const current = state.nodes[node_id];
       if (!current) return state;

       // Terminal state guard: terminal states cannot be downgraded
       const isCurrentTerminal = ["success", "warning", "error", "skipped"].includes(current.status);
       if (isCurrentTerminal && (status === "queued" || status === "running")) {
         return state;
       }

       return {
         ...state,
         nodes: {
           ...state.nodes,
           [node_id]: {
             ...current,
             status,
             detail: detail ?? current.detail,
             metrics: { ...current.metrics, ...metrics },
             lastUpdated: event.ts,
           },
         },
       };
     }
     ```

## Rules (do / don't)
- **DO** use monotonic sequence numbers (`seq`) or timestamps to discard late out-of-order SSE arrivals during reconnects.
- **DO** set `skipped` immediately for platforms not requested in the brief (e.g., if seller only checked Amazon, set Myntra & Flipkart to `skipped`).
- **DO** include concrete execution metrics in node details (e.g. `cache_hit: true`, `duration_ms: 850`).
- **DON'T** mutate canvas node objects directly; update the centralized state store.
- **DON'T** allow a node to transition backward from a terminal state to `running` or `queued`.

## Examples
See `examples/event-fixtures.json` for full event traces:
1. `happy_path_run`: All 4 agents and channels succeed cleanly.
2. `blocked_platform_run`: Amazon succeeds, Flipkart triggers robot-check warning, Reddit skips.
3. `cancelled_run`: Pipeline aborted midway due to client disconnect.

## Checklist before finishing
- [ ] All 14 node IDs mapped to appropriate pipeline stages.
- [ ] State machine enforces strict forward-only transitions.
- [ ] Backend emits `node` event type with typed payload and metrics.
- [ ] Frontend reducer is idempotent against SSE replays and reconnects.
- [ ] Edge states automatically derived from connected node statuses.
