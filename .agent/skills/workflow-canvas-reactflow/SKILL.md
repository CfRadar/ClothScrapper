---
name: workflow-canvas-reactflow
description: Guides the implementation of n8n-style workflow canvas graphs using React Flow v12 (@xyflow/react), memoized node/edge definitions, layout persistence, custom edge animations, and accessibility. Use when building or refactoring node graph visualization components.
---

# Workflow Canvas ReactFlow

## Purpose
This skill establishes standards and implementation patterns for rendering the Marketplace Keyword Agent pipeline as an interactive, n8n-style workflow node canvas using React Flow v12 (`@xyflow/react`). It ensures high visual fidelity, buttery 60fps pan/zoom performance, resilient layout persistence via local storage with Zod schema validation, dark/light theme alignment, and reduced-motion accessibility.

## When to use
- When creating or modifying the node graph workflow canvas component.
- When configuring custom node types, custom status-driven edges, or canvas controls.
- When managing node positions, grid snapping, and layout persistence across sessions.
- When configuring canvas zoom, panning, minimap, or viewport responsiveness.

## Step-by-step procedure

1. **Install and Import React Flow v12**:
   - Use official `@xyflow/react` v12 packages:
     ```typescript
     import {
       ReactFlow,
       ReactFlowProvider,
       Background,
       Controls,
       MiniMap,
       Handle,
       Position,
       BaseEdge,
       getBezierPath,
       useReactFlow,
       type Node,
       type Edge,
       type NodeProps,
       type EdgeProps,
     } from "@xyflow/react";
     import "@xyflow/react/dist/style.css";
     ```

2. **Define Node and Edge Types Outside Components**:
   - Never instantiate `nodeTypes` or `edgeTypes` inside a React component render function to prevent catastrophic re-mount loops:
     ```typescript
     const nodeTypes = {
       workflowNode: WorkflowNodeMemo,
       gatewayNode: GatewayNodeMemo,
     };

     const edgeTypes = {
       animatedStatusEdge: AnimatedStatusEdgeMemo,
     };
     ```

3. **Wrap Custom Nodes in `React.memo`**:
   - Ensure custom node components only re-render when their specific data properties change:
     ```tsx
     import { memo } from "react";

     export const WorkflowNode = memo(({ id, data, selected }: NodeProps<WorkflowNodeData>) => {
       return (
         <div
           role="group"
           aria-label={`${data.label} node - Status: ${data.status}`}
           className="relative flex items-center gap-3 px-3.5 py-2.5 rounded-lg border bg-surface text-foreground shadow-sm transition-colors duration-150"
         >
           <Handle type="target" position={Position.Left} className="!w-2 !h-2 !bg-border" />
           <StatusDot status={data.status} />
           <div className="flex flex-col min-w-0">
             <span className="text-[13px] font-medium leading-none truncate">{data.label}</span>
             {data.detail && <span className="text-[11px] text-muted-foreground truncate mt-1">{data.detail}</span>}
           </div>
           <Handle type="source" position={Position.Right} className="!w-2 !h-2 !bg-border" />
         </div>
       );
     });
     WorkflowNode.displayName = "WorkflowNode";
     ```

4. **Apply Canvas Settings for Fixed Workflow Execution**:
   - Configure the canvas for exploration without structural destruction:
     ```tsx
     <ReactFlow
       nodes={nodes}
       edges={edges}
       onNodesChange={onNodesChange}
       nodeTypes={nodeTypes}
       edgeTypes={edgeTypes}
       nodesDraggable={true}
       nodesConnectable={false}
       deleteKeyCode={null}
       snapToGrid={true}
       snapGrid={[8, 8]}
       minZoom={0.3}
       maxZoom={1.6}
       zoomOnScroll={true}
       panOnDrag={true}
       selectionOnDrag={false}
       fitView={true}
       fitViewOptions={{ padding: 0.2 }}
       onlyRenderVisibleElements={true}
       colorMode={theme} // "light" | "dark"
       proOptions={{ hideAttribution: false }} // Keep default React Flow attribution
     >
       <Background gap={16} size={1} color="var(--canvas-grid-dots)" />
       <MiniMap
         pannable
         zoomable
         className="!bottom-4 !left-4 !bg-surface !border !border-border !rounded-md"
         nodeColor={getMiniMapNodeColor}
       />
       <Controls className="!bottom-4 !right-4 !bg-surface !border !border-border !rounded-md shadow-sm" />
     </ReactFlow>
     ```

5. **Persist Layout in localStorage with Zod Validation**:
   - Store node coordinates under key `mka.layout.v1`. Validate strictly with Zod upon loading to safely discard corrupt or outdated layouts:
     ```typescript
     import { z } from "zod";

     const LayoutSchema = z.record(
       z.string(),
       z.object({
         x: z.number(),
         y: z.number(),
       })
     );

     export function loadPersistedLayout(): Record<string, { x: number; y: number }> | null {
       try {
         const raw = localStorage.getItem("mka.layout.v1");
         if (!raw) return null;
         const parsed = JSON.parse(raw);
         const validated = LayoutSchema.safeParse(parsed);
         return validated.success ? validated.data : null;
       } catch {
         return null;
       }
     }

     export function persistLayout(nodes: Node[]): void {
       const layout: Record<string, { x: number; y: number }> = {};
       for (const node of nodes) {
         layout[node.id] = { x: node.position.x, y: node.position.y };
       }
       localStorage.setItem("mka.layout.v1", JSON.stringify(layout));
     }

     export function resetLayout(): void {
       localStorage.removeItem("mka.layout.v1");
     }
     ```

6. **Animated Edge with Motion Accessibility**:
   - Render animated dash flow on running edges, but disable animation under `prefers-reduced-motion`:
     ```tsx
     export const AnimatedStatusEdge = memo(({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps) => {
       const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
       const isActive = data?.status === "active";
       const isError = data?.status === "error";

       return (
         <g className="react-flow__edge">
           <BaseEdge
             id={id}
             path={edgePath}
             className={`transition-colors duration-200 ${
               isError ? "!stroke-danger" : isActive ? "!stroke-accent" : "!stroke-border"
             }`}
             style={{ strokeWidth: 1.5 }}
           />
           {isActive && (
             <path
               d={edgePath}
               fill="none"
               className="stroke-accent stroke-[1.5] [stroke-dasharray:6,6] motion-safe:animate-[edgeFlow_1s_linear_infinite]"
             />
           )}
         </g>
       );
     });
     ```

## Rules (do / don't)
- **DO** keep the static workflow graph definition separate from live SSE status updates.
- **DO** derive node/edge presentation from the run state store instead of mutating node objects directly.
- **DO** support "Reset layout" to let sellers restore the pristine default layout.
- **DO** keep the default React Flow attribution displayed proudly.
- **DON'T** allow user node deletion or connect-handle interactions (`nodesConnectable={false}`, `deleteKeyCode={null}`).
- **DON'T** use inline object definitions for `nodeTypes` or `edgeTypes`.
- **DON'T** animate edges when `prefers-reduced-motion` is active.

## Examples
See `examples/graph-definition.ts` for the complete static typed node and edge registry for the 4-agent marketplace keyword pipeline.

## Checklist before finishing
- [ ] `nodeTypes` and `edgeTypes` declared outside component tree.
- [ ] All custom nodes wrapped in `React.memo`.
- [ ] Dotted `Background`, `MiniMap`, and `Controls` styled with theme tokens.
- [ ] `nodesConnectable={false}` and `deleteKeyCode={null}` enforced.
- [ ] Dragged positions safely stored in `mka.layout.v1` and validated with Zod.
- [ ] Edge animations respect `prefers-reduced-motion`.
- [ ] Visual review verified via `scripts/screenshot_canvas.mjs`.
