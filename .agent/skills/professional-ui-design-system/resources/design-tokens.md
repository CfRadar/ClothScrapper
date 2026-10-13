# Design Tokens: Professional Graphite Palette

This document defines the exact color hex tokens, font stacks, and CSS variables for the application.

## 1. Theme Color Tokens

| Token Name | CSS Variable | Dark Theme (Hex) | Light Theme (Hex) | Purpose |
|---|---|---|---|---|
| **Background** | `--bg-canvas` | `#0C0D0E` | `#FFFFFF` | Canvas and page background |
| **Surface** | `--bg-surface` | `#141517` | `#F9FAFB` | Card, node, and drawer background |
| **Surface Sunken** | `--bg-surface-sunken`| `#101113` | `#F3F4F6` | Segmented controls, input wells |
| **Surface Hover** | `--bg-surface-hover` | `#1A1C1F` | `#F3F4F6` | Button and row hover state |
| **Surface Active**| `--bg-surface-active`| `#222428` | `#E5E7EB` | Pressed button or selected item |
| **Border** | `--border-subtle` | `#222428` | `#E5E7EB` | Default 1px card and node borders |
| **Border Strong** | `--border-strong` | `#2E3136` | `#D1D5DB` | Input borders, focused dividers |
| **Foreground** | `--text-primary` | `#F3F4F6` | `#111827` | Headings, active values, primary text |
| **Foreground Muted**| `--text-muted` | `#9CA3AF` | `#6B7280` | Subheadings, details, descriptions |
| **Foreground Faint**| `--text-faint` | `#6B7280` | `#9CA3AF` | Placeholders, disabled states |
| **Accent** | `--accent-primary` | `#3B82F6` | `#2563EB` | Selected tabs, active edges, primary buttons |
| **Accent Hover** | `--accent-hover` | `#60A5FA` | `#1D4ED8` | Primary button hover |
| **Accent Subtle**| `--accent-subtle` | `#1E293B` | `#EFF6FF` | Active row tints, badges |
| **Success** | `--status-success` | `#10B981` | `#059669` | Success node dot, verified state |
| **Warning** | `--status-warning` | `#F59E0B` | `#D97706` | Blocked platform notice, rate-limit warnings |
| **Danger** | `--status-danger` | `#EF4444` | `#DC2626` | Execution errors, critical alerts |
| **Skipped** | `--status-skipped` | `#64748B` | `#94A3B8` | Skipped optional scrapers |

---

## 2. Typography Tokens

```css
:root {
  --font-sans: 'Inter Variable', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono Variable', SFMono-Regular, Menlo, Monaco, Consolas, monospace;

  --text-xs: 11px;
  --text-sm: 13px; /* Default UI Body */
  --text-base: 14px;
  --text-md: 15px; /* Section Headings */
  --text-lg: 18px; /* App & Modal Titles */

  --leading-tight: 1.25;
  --leading-normal: 1.45;
}
```

---

## 3. Radii and Spacing

```css
:root {
  --radius-xs: 4px;
  --radius-sm: 6px; /* Buttons, inputs, chips */
  --radius-md: 8px; /* Cards, nodes, drawer */
  --radius-full: 9999px; /* Status dots */

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
}
```

---

## 4. Canvas-Specific Tokens

| Token | Dark | Light | Description |
|---|---|---|---|
| `--canvas-grid-dots` | `#222428` | `#E5E7EB` | React Flow background dot pattern |
| `--node-bg` | `#141517` | `#FFFFFF` | Node container background |
| `--node-border-idle` | `#222428` | `#E5E7EB` | Idle node border |
| `--node-border-active` | `#3B82F6` | `#2563EB` | Running node border highlight |
| `--edge-idle` | `#222428` | `#E5E7EB` | Static inactive edge stroke |
| `--edge-active` | `#3B82F6` | `#2563EB` | Active pulsing animated stroke |
