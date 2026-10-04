---
name: react-clean-ui
description: Governs the React 18, Vite, TypeScript, and Tailwind CSS v3.4 frontend. Use when implementing the single-screen brief input form, thin real-time progress strip, clutter-free platform keyword cards with copy-all buttons, distinct "Other factors" section, and interactive chat block.
---

# React Clean UI

## Purpose
This skill establishes the user interface design, component layout, and frontend data-fetching patterns for the **Marketplace Keyword Agent**. Built on React 18, Vite, TypeScript, Tailwind CSS v3.4, and Lucide icons, it enforces a zero-clutter, utility-first UI: clean keyword chips per platform, no distracting charts or vanity metrics, an accessible real-time progress strip, a dedicated "Other factors" section, and a responsive chat block.

## When to use
- When creating or modifying frontend components (`BriefForm`, `ProgressStrip`, `PlatformResults`, `OtherFactors`, `ChatBlock`).
- When implementing the SSE streaming hook (`useRunStream`).
- When styling components with Tailwind CSS following `resources/design-tokens.md`.
- When ensuring accessibility standards (labels, focus outlines, `aria-live` status regions).

## UI Layout Architecture (Single Screen Flow)
```
+---------------------------------------------------------------+
| App Header: Marketplace Keyword Agent  [Quota: 138 calls left] |
+---------------------------------------------------------------+
| 1. Seller Brief Input Form                                    |
|    - Textarea: T-shirt description, fabric, fit, theme...     |
|    - Platform Checkboxes: [x] Amazon.in  [x] Myntra  [x] FK   |
|    - [ Generate Keywords Button ]                             |
+---------------------------------------------------------------+
| 2. Thin Live Progress Strip (Hidden when idle)                |
|    [=== 60% ===] Scraping Amazon & Reddit...                  |
+---------------------------------------------------------------+
| 3. Platform Results (Grid: 1 Card per platform)               |
|    +-----------------------------+--------------------------+ |
|    | Amazon.in        [Copy All] | Myntra        [Copy All] | |
|    | [oversized tee] [cotton]... | [drop shoulder] [baggy]..| |
|    +-----------------------------+--------------------------+ |
+---------------------------------------------------------------+
| 4. Other Factors Section (Visually distinct box)              |
|    - Fabric/GSM recommendations (e.g., 240 GSM for oversize) |
|    - Price point & combo suggestions                         |
|    - Trademark/Brand flags & policy alerts                    |
+---------------------------------------------------------------+
| 5. Interactive Chat Block                                     |
|    - History of user queries & Analyst follow-up answers      |
|    - [ Ask a question or customize... ]              [Send]   |
+---------------------------------------------------------------+
```

## Step-by-step procedure

1. **Implement Single Brief Input Form**:
   - Multi-line textarea with placeholder guiding detailed entry (fit, neck, sleeve, GSM, prints, target demographic).
   - Multi-select toggle buttons for target platforms (Amazon.in, Myntra, Flipkart).
   - Clean Submit button with loading spinner state and keyboard shortcut (`Cmd+Enter` / `Ctrl+Enter`).

2. **Implement Thin Live Progress Strip**:
   - Placed immediately between the form and results.
   - Height: 4px to 8px progress bar with an accompanying one-line text status.
   - Accessibility: Must use `role="status"` and `aria-live="polite"` so screen readers announce stage transitions.
   - Smooth animated transition between `Planner` -> `Scraping` -> `Scoring` -> `Analyst`.

3. **Render Clean Platform Keyword Cards**:
   - Exactly one card per selected platform.
   - Card Header: Platform badge icon (Amazon / Myntra / Flipkart) + Count + "Copy All" button.
   - Card Body: Clean list of clickable keyword chips.
     - Single click copies individual keyword to clipboard with temporary visual feedback (checkmark).
     - "Copy All" copies newline-separated or comma-separated list formatted for direct paste into Seller Central / Flipkart portal.
   - **STRICT PROHIBITION**: No search volume bars, no confidence percentages, no metric dials.

4. **Render Visually Distinct "Other Factors" Section**:
   - Visually separated from the platform keyword cards using distinct border styling or subtle slate background tint.
   - Contains Markdown-rendered strategic intelligence:
     - Recommended GSM & fabric specs.
     - Pricing tier observation from scraped data.
     - Trademark / policy infringement warnings (e.g. flagged celebrity/anime names).

5. **Implement Interactive Chat Block**:
   - Collapsible or docked at bottom.
   - Allows seller to ask follow-up questions to the AI Analyst (e.g., "Give me 10 keywords focused purely on gym wear").
   - Maintains chat message history and handles streaming responses.

6. **Create Custom SSE Streaming Hook (`useRunStream`)**:
   - Uses `fetch` with `ReadableStream` reader (or `EventSource`) to connect to `/api/runs/{run_id}/stream`.
   - Dispatches incoming typed events directly into React component state:
     - `stage`: Updates progress strip text and progress percentage.
     - `partial`: Pre-populates platform chips as soon as a scraper finishes.
     - `complete`: Finalizes keyword lists and displays "Other factors".
     - `error`: Shows an alert banner without wiping prior state.

## Rules (do / don't)
- **DO** use the design tokens defined in `resources/design-tokens.md`.
- **DO** provide a "Copy All" button on each platform card for 1-click clipboard copying.
- **DO** use `aria-live="polite"` on the progress strip for accessibility.
- **DON'T** display keyword scores, confidence bars, search volume guesses, or graphs inside the platform keyword cards.
- **DON'T** include marketing text, promotional banners, or extraneous decorative elements.
- **DON'T** use Tailwind classes outside the curated palette (stick to Slate/Zinc and subtle brand accents).

## Examples

### SSE Stream Hook Pattern (`useRunStream.ts`)
```typescript
import { useState, useEffect } from "react";

interface SSEEvent {
  type: "status" | "progress" | "partial" | "complete" | "error";
  stage: string;
  message: string;
  data?: any;
}

export function useRunStream(runId: string | null) {
  const [progress, setProgress] = useState<{ stage: string; message: string }>({ stage: "idle", message: "" });
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    const eventSource = new EventSource(`/api/runs/${runId}/stream`);

    eventSource.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      if (event.type === "progress" || event.type === "status") {
        setProgress({ stage: event.stage, message: event.message });
      } else if (event.type === "complete") {
        setResult(event.data);
        eventSource.close();
      } else if (event.type === "error") {
        setError(event.message);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setError("Stream connection lost.");
      eventSource.close();
    };

    return () => eventSource.close();
  }, [runId]);

  return { progress, result, error };
}
```

## Checklist before finishing
- [ ] Single input brief form with platform selection implemented.
- [ ] Real-time progress strip uses `aria-live="polite"` and thin layout.
- [ ] Platform keyword cards show ONLY clean chips and a "Copy All" button.
- [ ] Zero scores, numbers, charts, or volume estimates displayed in keyword cards.
- [ ] "Other factors" section visually distinct with markdown support.
- [ ] Chat block allows interactive follow-ups with the Analyst agent.
- [ ] Follows tokens in `resources/design-tokens.md`.
