---
name: results-drawer-ux
description: Governs the right-side results drawer UX, including the resizable dragging handle, Radix tab navigation, keyword chips presentation, CSV export with formula injection guards, and canvas push layout. Use when implementing or updating the results drawer.
---

# Results Drawer UX

## Purpose
This skill establishes the user experience and implementation specifications for the right-side results drawer. The drawer presents the output of the 4-agent keyword intelligence run in a structured, focused panel while keeping the workflow canvas visible, accessible, and responsive.

## When to use
- When implementing or updating the right-side results panel.
- When configuring drawer tabs (Keywords, Other factors, Chat, Run details).
- When implementing drawer resize dragging, width persistence, or arrow handle toggles.
- When formatting keyword exports (copy-all, CSV export with formula-injection sanitization).

## Core UX Mechanics

1. **Collapsible Drawer with Arrow Handle**:
   - Default width: **440px**.
   - Resizable range: **360px to 720px** by dragging the left border handle.
   - Persistence: Save current width in `localStorage` under `mka.drawer.width.v1`.
   - Always-Visible Handle: Attached to the drawer's left edge. Displays a chevron icon (`ChevronLeft` / `ChevronRight`) indicating toggle direction.
   - **Auto-Open & Badge**: Opens automatically once when a run transitions to `completed` or `result`. If the user manually closes the drawer while results exist, display an unread indicator dot on the handle.

2. **Canvas Push Layout (Not Overlay)**:
   - The drawer must **push** the canvas container instead of hovering over it.
   - When the drawer expands or resizes, the React Flow canvas container adjusts its width (`width: calc(100% - ${drawerWidth}px)`).
   - The canvas `MiniMap` and `Controls` automatically shift so they are never obscured or clipped by the drawer.

3. **Radix Tabs Architecture**:
   - Four distinct tabs:
     1. **Keywords**: Clean platform sections with keyword chips, copy-all, and CSV export.
     2. **Other factors**: Structured factors (title formula, recommended title, negative keywords, price band, competition, seasonality).
     3. **Chat**: Interactive AI customization with keywords patch support.
     4. **Run details**: Execution telemetry (duration, cache hits, LLM calls used, model names, raw event log).
   - **Keyboard Navigation**:
     - `ArrowLeft` / `ArrowRight`: Navigate between tabs.
     - `Escape`: Closes the drawer and returns focus to the arrow handle.

4. **Keywords Tab & Export Hygiene**:
   - **Strict Presentation**: Exactly one section per requested platform containing **only keyword chips** and export controls. No search volume numbers, no confidence scores, no charts.
   - **Copy All**: Copies a comma-separated list of keywords to the clipboard with temporary visual feedback.
   - **CSV Export with Formula Injection Guard**:
     - Spreadsheet software (Excel, Google Sheets, LibreOffice) executes cells starting with `=`, `+`, `-`, or `@` as formulas, enabling CSV injection attacks.
     - **Rule**: Every exported keyword cell starting with `=, +, -, @` or tab/CR must be prefixed with a single quote (`'`).

## Step-by-step procedure

1. **Implement Drawer Resize Hook**:
   ```typescript
   export function useDrawerResize(defaultWidth = 440, minWidth = 360, maxWidth = 720) {
     const [width, setWidth] = useState(() => {
       const saved = localStorage.getItem("mka.drawer.width.v1");
       return saved ? Math.min(maxWidth, Math.max(minWidth, Number(saved))) : defaultWidth;
     });
     const [isResizing, setIsResizing] = useState(false);

     const startResizing = useCallback(() => setIsResizing(true), []);
     const stopResizing = useCallback(() => setIsResizing(false), []);

     const resize = useCallback((mouseMoveEvent: MouseEvent) => {
       if (!isResizing) return;
       const newWidth = document.body.clientWidth - mouseMoveEvent.clientX;
       if (newWidth >= minWidth && newWidth <= maxWidth) {
         setWidth(newWidth);
         localStorage.setItem("mka.drawer.width.v1", String(newWidth));
       }
     }, [isResizing, minWidth, maxWidth]);

     useEffect(() => {
       if (!isResizing) return;
       window.addEventListener("mousemove", resize);
       window.addEventListener("mouseup", stopResizing);
       return () => {
         window.removeEventListener("mousemove", resize);
         window.removeEventListener("mouseup", stopResizing);
       };
     }, [isResizing, resize, stopResizing]);

     return { width, isResizing, startResizing };
   }
   ```

2. **Implement Safe CSV Export**:
   ```typescript
   export function exportKeywordsToCSV(platform: string, keywords: string[]): void {
     // Guard against CSV / Spreadsheet Formula Injection
     const sanitizeCell = (cell: string): string => {
       const trimmed = cell.trim();
       if (/^[=+\-@\t\r]/.test(trimmed)) {
         return `'${trimmed.replace(/"/g, '""')}`;
       }
       return `"${trimmed.replace(/"/g, '""')}"`;
     };

     const rows = [
       ["Platform", "Keyword"],
       ...keywords.map((kw) => [sanitizeCell(platform), sanitizeCell(kw)]),
     ];

     const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
     const encodedUri = encodeURI(csvContent);
     const link = document.createElement("a");
     link.setAttribute("href", encodedUri);
     link.setAttribute("download", `${platform}-keywords-${Date.now()}.csv`);
     document.body.appendChild(link);
     link.click();
     document.body.removeChild(link);
   }
   ```

3. **Handle Canvas Push Transition**:
   - Ensure the layout wrapper divides width between canvas and drawer smoothly:
     ```tsx
     <div className="flex w-screen h-screen overflow-hidden bg-background">
       <div
         className="relative flex-1 h-full transition-[width] duration-150 ease-out"
         style={{ width: isOpen ? `calc(100% - ${width}px)` : "100%" }}
       >
         <WorkflowCanvas />
       </div>
       <ResultsDrawer width={width} isOpen={isOpen} onToggle={toggleDrawer} />
     </div>
     ```

## Rules (do / don't)
- **DO** push the canvas viewport so the canvas nodes and controls are never occluded.
- **DO** sanitize all exported keywords against spreadsheet formula injection.
- **DO** restore focus to the drawer toggle handle when `Escape` is pressed.
- **DON'T** display scores, volume bars, or marketing commentary inside platform keyword sections.
- **DON'T** let the drawer shrink below 360px or exceed 720px.

## Checklist before finishing
- [ ] Drawer width defaults to 440px and resizes smoothly between 360px and 720px.
- [ ] Drawer pushes canvas; controls and minimap shift without clipping.
- [ ] Arrow handle indicates toggle direction and shows unread badge when closed with ready results.
- [ ] Keywords tab contains strictly keyword chips, "Copy all", and "Export CSV".
- [ ] CSV export enforces single-quote escaping for formula injection characters (`=`, `+`, `-`, `@`).
- [ ] Radix Tabs support full keyboard navigation (`Arrow` keys, `Esc` to close).
