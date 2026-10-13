---
name: frontend-a11y-and-qa
description: Guides frontend accessibility (WCAG AA), automated testing with Vitest/RTL and Playwright Test, axe-core scans, mock SSE fixture server, visual regression snapshots, and keyboard navigation audits. Use when writing tests or verifying frontend UX compliance.
---

# Frontend Accessibility and QA

## Purpose
This skill establishes quality assurance standards and accessibility (WCAG 2.1 AA) compliance for the frontend. It covers automated unit testing with Vitest and React Testing Library, end-to-end integration and accessibility audits with Playwright and `@axe-core/playwright`, fixture-driven mock SSE streaming, and visual defect triage using browser tools.

## When to use
- When creating or running frontend automated tests.
- When performing accessibility audits (contrast ratios, focus traps, aria attributes).
- When validating canvas interactions with simulated backend runs via `mock_sse_server.mjs`.
- When capturing multi-viewport screenshots (1440x900, 1024x768) in light and dark mode.

## Testing & QA Tooling Stack

| Tool | Purpose | Primary Scope |
|---|---|---|
| **Vitest + RTL** | Component unit tests | Form validation, chip rendering, reducer state transitions |
| **Playwright Test** | End-to-end flows | Canvas panning/zooming, drawer resizing, full run cycles |
| **@axe-core/playwright** | Automated a11y scans | WCAG 2.1 AA violations, color contrast, missing ARIA |
| **mock_sse_server.mjs** | Offline backend mock | Replaying timed SSE fixtures without consuming LLM quota |

## Accessibility Guardrails (WCAG 2.1 AA)
1. **Never Convey Status by Color Alone**:
   - Every node status dot or badge must be accompanied by an icon (`CheckCircle`, `AlertTriangle`, `Loader2`, `XCircle`) and textual status in `aria-label` or visible text.
2. **Keyboard Traversal & Focus Rings**:
   - Every canvas node must have `tabIndex={0}`, `role="group"`, and an `aria-label` detailing its name, category, and live status.
   - Visible focus rings (`focus-visible:ring-2 focus-visible:ring-accent`) must appear on keyboard navigation.
3. **Contrast Ratios**:
   - All body text (13px) and helper labels (11px) must meet at least **4.5:1** contrast against their surface backgrounds in both light and dark modes.
4. **Motion Sensitivity (`prefers-reduced-motion`)**:
   - Edge dashing animations, pulse dots, and drawer push transitions must respect `prefers-reduced-motion: reduce`.

## Step-by-step procedure

1. **Start Mock SSE Fixture Server**:
   - Use the standalone Node server to test without needing the Python backend:
     ```bash
     node .agent/skills/frontend-a11y-and-qa/scripts/mock_sse_server.mjs 8000
     ```

2. **Execute Automated Accessibility Audit with Playwright & Axe**:
   ```typescript
   import { test, expect } from "@playwright/test";
   import AxeBuilder from "@axe-core/playwright";

   test("canvas and drawer meet WCAG 2.1 AA", async ({ page }) => {
     await page.goto("http://localhost:5173");
     await page.waitForSelector(".react-flow");

     const accessibilityScanResults = await new AxeBuilder({ page })
       .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
       .analyze();

     expect(accessibilityScanResults.violations).toEqual([]);
   });
   ```

3. **Verify Scenarios with Mock Events**:
   - **Happy Path**: Full run progresses from Planner to Analyst, completes, and opens the drawer with results.
   - **Blocked Platform**: Retail platform blocks with robot-check; canvas node turns amber warning; run completes with warning banner.
   - **Cancelled Run**: Client abort cancels pipeline; canvas nodes freeze with clear status indicator.
   - **Quota Exceeded**: Quota badge turns red; submission disabled with informative toast.
   - **Backend Offline**: Banner surfaces connection failure; retry action provided.

4. **Visual Inspection via Browser Tool**:
   - Launch the Antigravity browser subagent or capture multi-viewport screenshots:
     - 1440 × 900 (Desktop) in Dark and Light themes.
     - 1024 × 768 (Tablet/Laptop) in Dark and Light themes.
   - Check typography clipping, drawer resize margins, and focus ring alignment.

## Rules (do / don't)
- **DO** test both light and dark themes for contrast compliance.
- **DO** verify keyboard navigation through the entire canvas and drawer using only `Tab`, `Arrow`, and `Enter` keys.
- **DO** use `mock_sse_server.mjs` during local frontend development to prevent exhausting OpenRouter quota.
- **DON'T** suppress axe-core violations with arbitrary ignore rules.
- **DON'T** test real retail scrapers or live LLM APIs in frontend unit tests.

## Examples
See `scripts/mock_sse_server.mjs` for the executable fixture replay server.

## Checklist before finishing
- [ ] Vitest unit tests pass (`npm test -- --run`).
- [ ] Playwright axe-core audit reports 0 violations.
- [ ] Canvas nodes have `role="group"` and comprehensive `aria-label` attributes.
- [ ] No status is communicated purely by color.
- [ ] Drawer and canvas behave properly under `prefers-reduced-motion`.
- [ ] Visual screenshots captured at 1440x900 and 1024x768 in light and dark mode.
