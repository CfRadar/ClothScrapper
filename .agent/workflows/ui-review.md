---
name: ui-review
description: Executes a visual and accessibility review of the workflow canvas and results drawer by launching the mock SSE server, capturing multi-viewport screenshots in light and dark mode, running axe scans, and auditing UI defects using the browser tool.
---

# Workflow: ui-review

Execute this workflow whenever styling, layout, canvas nodes, or the results drawer are modified to verify compliance with the `professional-ui-design-system` and accessibility standards.

## Prerequisites
- Node.js dependencies installed (`cd frontend && npm install`).
- Playwright Chromium installed (`npx playwright install chromium`).

---

## Step-by-Step Execution Procedure

### Step 1: Start Mock SSE Server & Frontend
1. Launch the standalone mock SSE server in terminal 1:
   ```bash
   node .agent/skills/frontend-a11y-and-qa/scripts/mock_sse_server.mjs 8000
   ```
2. Launch the frontend development server in terminal 2:
   ```bash
   cd frontend && npm run dev
   ```
3. Verify that `http://localhost:5173` loads and connects to `http://localhost:8000/api/health`.

### Step 2: Capture Visual Screenshots across Viewports & Themes
Execute the canvas screenshot capture script:
```bash
node .agent/skills/workflow-canvas-reactflow/scripts/screenshot_canvas.mjs http://localhost:5173 screenshots/
```
Verify generated PNGs in `screenshots/`:
- `canvas-desktop-1440x900-dark.png`
- `canvas-desktop-1440x900-light.png`
- `canvas-tablet-1024x768-dark.png`
- `canvas-tablet-1024x768-light.png`

### Step 3: Run Automated Accessibility (Axe) Scans
Run the Playwright axe-core audit suite:
```bash
cd frontend && npx vitest run --testNamePattern="a11y"
```
Ensure 0 critical or serious WCAG 2.1 AA violations are reported.

### Step 4: Visual Defect Audit via Browser Tool
1. Use the Antigravity browser subagent or inspect screenshots against `.agent/skills/professional-ui-design-system/resources/ui-review-checklist.md`:
   - [ ] No gradient hero text, purple/blue glows, or glassmorphism.
   - [ ] 1px subtle borders (`border-border`) used instead of heavy shadows.
   - [ ] Base body text is 13px Inter; keyword chips use JetBrains Mono.
   - [ ] Drawer width defaults to 440px and resizes between 360px and 720px by dragging handle.
   - [ ] Canvas `MiniMap` and `Controls` shift when drawer expands; no occlusion.
   - [ ] Sentence case applied across headings and buttons with zero exclamation marks.
2. If visual defects or alignment issues are identified, refine styling and repeat Steps 2-4 until zero defects remain.
