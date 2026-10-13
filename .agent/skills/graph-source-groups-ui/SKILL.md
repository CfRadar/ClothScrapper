---
name: graph-source-groups-ui
description: UI specifications and layout algorithms for scaling the React Flow canvas to 40+ sources using collapsible group nodes, compact source cards (168x56), dynamic registry generation, and source health popovers. Trigger when updating the workflow graph or source visualization.
---

# Graph Source Groups UI

## Purpose
Governs the visual scaling of the React Flow canvas (`@xyflow/react`) as external sources expand from 6 to 40+. Prevents canvas clutter through collapsible category group containers, compact 168x56 px source node cards, deterministic grid auto-layout, and dynamic graph derivation from the backend registry.

---

## When to Use
- Implementing or styling category group containers on the workflow graph.
- Converting individual source nodes into compact 168x56 px cards.
- Connecting the React Flow canvas dynamically to `GET /api/sources`.
- Adding the "Sources" toolbar popover and live health indicators.

---

## Core Visual Specifications

### 1. Group Containers (`GroupNode`)
- **Type**: `group`
- **Children**: Use `parentId: "<group_id>"` and `extent: "parent"`.
- **Categories**:
  1. `group_b2c`: "B2C marketplaces" (Amazon, Myntra, Flipkart, Ajio, Snapmint)
  2. `group_b2b`: "B2B and wholesale" (IndiaMART, ExportersIndia, Alibaba)
  3. `group_quickcommerce`: "Quick commerce" (Blinkit, Swiggy Instamart, Zepto, Toing)
  4. `group_signals`: "Search and social" (Google, Pinterest, Meta Ads, Reddit, X, Instagram)
- **Styling**:
  - Background: `--surface` at 40% opacity with subtle 1px `--border`.
  - Header (32 px): Group label (12 px bold), source count badge, collapse/expand chevron.
  - Padding: 16 px padding around children.
- **Collapsed State**:
  - When collapsed, children nodes hide and the group card shrinks to a single pill (220x40 px) displaying a summary line:
    `"6 sources, 4 done, 1 blocked"`.

---

### 2. Compact Source Node (`168x56 px`)
Replaces large individual cards with an ultra-clean, dense format:

```text
+------------------------------------------+
| [Icon] Amazon.in                 [● Done]|
| [Sell Target]                     507 ms |
+------------------------------------------+
```

- **Dimensions**: Exactly 168 px width, 56 px height.
- **Top Row**: 16 px icon tile, source name (11 px semi-bold, truncated), semantic status badge/dot.
- **Bottom Row**: Small pill tag (`Sell target` in accent soft, or `Signal` in slate), right-aligned latency/item count in JetBrains Mono 10 px.
- **Status Override / Disabled**:
  Rendered at **55% opacity** with strikethrough or muted badge.
- **Hover / Tooltip**:
  Hovering displays a Radix tooltip with:
  - Relevance: High / Medium / Low
  - ToS Risk: Low / Medium / High
  - Last Strategy Used: `suggestion_api` | `embedded_state` | `network_capture` | `dom_selector`
  - Failure Cause (if degraded/blocked): e.g. "needs_location" or "Robot check triggered"

---

## Deterministic Auto-Layout Algorithm

Never hardcode source coordinates manually. The graph is computed dynamically from `GET /api/sources`:

```typescript
export function computeGroupSourceLayout(
  groupX: number,
  groupY: number,
  sourceCount: number
) {
  const COL_WIDTH = 168;
  const ROW_HEIGHT = 56;
  const GAP_X = 16;
  const GAP_Y = 12;
  const PADDING = 16;
  const HEADER_HEIGHT = 40;

  // 2-column grid layout inside group
  const cols = 2;
  const rows = Math.ceil(sourceCount / cols);

  const groupWidth = PADDING * 2 + cols * COL_WIDTH + (cols - 1) * GAP_X;
  const groupHeight = PADDING * 2 + HEADER_HEIGHT + rows * ROW_HEIGHT + (rows - 1) * GAP_Y;

  const positions = [];
  for (let i = 0; i < sourceCount; i++) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions.push({
      x: PADDING + col * (COL_WIDTH + GAP_X),
      y: PADDING + HEADER_HEIGHT + row * (ROW_HEIGHT + GAP_Y),
    });
  }

  return { groupWidth, groupHeight, positions };
}
```

---

## Sources Popover & Quick Controls

- **Toolbar Button**: A "Sources" icon button with a count badge (e.g. `14 active`).
- **Popover Content**:
  - Grouped list of all registered sources.
  - Status indicator (Healthy / Degraded / Blocked / Unavailable).
  - Quick toggle switch (Enable/Disable per source).
  - "Check now" button triggering `POST /api/sources/{id}/check`.

---

## Rules (DO / DON'T)

### DO
- Build the graph dynamically from the backend registry `GET /api/sources`.
- Use `extent: "parent"` so dragging a group moves all contained source nodes.
- Maintain the 2-column grid with 32 px spacing between adjacent groups.
- Display a clear summary line when a group is collapsed.

### DON'T
- DO NOT hardcode individual source node coordinates in static layout files.
- DO NOT use full-sized 280 px agent cards for source nodes.
- DO NOT overlap nodes when new sources are enabled or added to the registry.

---

## Visual Verification

Verify canvas scaling using the headless screenshot utility:

```bash
node .agent/skills/graph-source-groups-ui/scripts/screenshot_canvas.mjs
```

Inspect output screenshots in `docs/screenshots/`:
- `canvas_groups_expanded_1440x900.png`
- `canvas_groups_collapsed_1440x900.png`

---

## Checklist Before Finishing
- [ ] Source nodes rendered in compact 168x56 px card dimensions.
- [ ] Collapsible group nodes support expanded and collapsed summary views.
- [ ] 2-column internal grid layout calculated deterministically.
- [ ] Disabled/unavailable sources rendered at 55% opacity with explanation tooltip.
- [ ] Screenshots verified at 1440x900 resolution.
