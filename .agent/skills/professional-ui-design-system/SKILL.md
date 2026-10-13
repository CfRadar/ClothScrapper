---
name: professional-ui-design-system
description: Defines the professional, restraint-driven design system for the application. Covers graphite palette tokens, 13px base typography, 4px grid spacing, crisp 1px borders, strict anti-patterns against AI-template tropes, and concrete component specifications. Use for all UI design and styling.
---

# Professional UI Design System

## Purpose
This skill establishes the visual principles, token foundations, component specifications, and copywriting standards required to build an interface that looks designed by a seasoned product engineer (e.g. Linear, n8n, Vercel), completely free from generic AI-generated template cliches.

## When to use
- When creating, styling, or refactoring React components.
- When configuring Tailwind CSS classes, CSS variables, or design tokens.
- When reviewing layouts, typography, spacing, states, or copywriting.
- When auditing the user interface for design quality and consistency.

## Visual Design Foundations

1. **Graphite Neutral Palette & Restrained Accent**:
   - Backgrounds: Neutral graphite shades (`#0C0D0E` dark, `#FFFFFF` light).
   - Surfaces: Subtly elevated cards (`#141517` dark, `#F9FAFB` light) with crisp 1px borders (`#222428` dark, `#E5E7EB` light).
   - Primary Accent: Restrained blue-slate or indigo (`#3B82F6` / `#2563EB`), never neon purple or cyan glows.
   - Semantic Statuses: Desaturated, high-readability indicators:
     - Success: Emerald (`#10B981` / `#059669`)
     - Warning: Amber (`#F59E0B` / `#D97706`)
     - Danger: Rose/Crimson (`#EF4444` / `#DC2626`)
     - Skipped/Muted: Slate (`#64748B` / `#94A3B8`)

2. **Typography**:
   - Base UI Font: **Inter Variable** (`@fontsource-variable/inter`), high legibility at small sizes.
   - Code & Metrics Font: **JetBrains Mono Variable** (`@fontsource-variable/jetbrains-mono`).
   - Base Density: **13px body text** (`text-[13px] leading-5`), **11px helper text** (`text-[11px] leading-4`).
   - Headings: Compact, bold without sprawling margins (`text-[15px] font-semibold`, `text-[18px] font-semibold`).

3. **Spatial Grid & Elevation**:
   - **4px Spatial Grid**: All margins, paddings, and heights must be exact multiples of 4px (`gap-1` = 4px, `gap-2` = 8px, `p-3` = 12px, `p-4` = 16px).
   - **Corner Radius**: Bounded strictly to **6px or 8px** (`rounded-md` or `rounded-lg`). Never use oversized pills (`rounded-3xl`) for cards.
   - **Elevation**: 1px subtle borders (`border border-border`) instead of heavy blurry drop-shadows.

4. **Icons**:
   - Exclusively `lucide-react`.
   - Fixed size: **16px** (`size-4` / `w-4 h-4`) with stroke width **1.5** (`strokeWidth={1.5}`).

## Explicit Anti-Patterns (Strictly Forbidden)
Any appearance of these tropes fails design review:
- ❌ **Gradient Hero Text**: (e.g. `bg-gradient-to-r from-purple-400 to-pink-600 bg-clip-text text-transparent`).
- ❌ **Purple / Blue Radial Glows**: (e.g. ambient blurry background orbs).
- ❌ **Glassmorphism**: (e.g. heavy `backdrop-blur-md bg-white/10`).
- ❌ **Emoji as Icons**: (e.g. 🚀, ✨, 🔥, 👕 in buttons or section headers).
- ❌ **Sparkle / Magic Wand Icons**: (e.g. `Sparkles` used indiscriminately on every AI action).
- ❌ **Oversized Rounded Cards**: (e.g. `rounded-3xl` or `rounded-2xl` on dense operational tools).
- ❌ **Stacked Heavy Drop Shadows**: (e.g. `shadow-2xl shadow-indigo-500/50`).
- ❌ **Marketing Copy**: (e.g. "Unlock the revolutionary power of AI for your apparel business").
- ❌ **Skeleton Shimmer Everywhere**: Simple, subtle spinner or plain low-opacity placeholder.

## Component Specifications

| Component | Heights | Padding | Style Spec | States (Hover / Focus / Disabled) |
|---|---|---|---|---|
| **Button (Primary)** | 28px (`sm`), 32px (`md`) | `px-2.5` (`sm`), `px-3` (`md`) | `bg-accent text-white font-medium rounded-md text-[13px]` | Hover: `bg-accent-hover`, Focus: `ring-2 ring-accent/30 ring-offset-1`, Disabled: `opacity-50 pointer-events-none` |
| **Button (Secondary)**| 28px (`sm`), 32px (`md`) | `px-2.5` (`sm`), `px-3` (`md`) | `bg-surface border border-border text-foreground rounded-md text-[13px]` | Hover: `bg-surface-hover border-border-hover`, Focus: focus ring, Disabled: `opacity-50` |
| **Button (Ghost)** | 28px (`sm`), 32px (`md`) | `px-2` | `text-muted-foreground hover:text-foreground hover:bg-surface-hover rounded-md` | Active: `bg-surface-active`, Focus: focus ring |
| **Keyword Chip** | 24px | `px-2 py-0.5` | `bg-surface border border-border rounded text-[12px] font-mono text-foreground select-all` | Hover: `border-accent/40`, Focus: focus ring |
| **Status Dot** | 8px × 8px | N/A | `rounded-full` (success: green-500, running: blue-500 animate-pulse, warning: amber-500, error: red-500) | Always paired with text label or tooltip |
| **Segmented Control**| 28px | `p-0.5` | Container: `bg-surface-sunken border border-border rounded-md`. Tab: `text-[12px] rounded` | Active tab: `bg-surface text-foreground shadow-xs` |
| **Input / Field** | 32px | `px-2.5 py-1.5` | `bg-surface border border-border rounded-md text-[13px] text-foreground placeholder:text-muted` | Focus: `border-accent ring-1 ring-accent`, Invalid: `border-danger` |
| **Drawer Header** | 44px | `px-4 py-2.5` | `border-b border-border bg-surface flex items-center justify-between` | Sticky, clean typography |

## Copywriting Rules
- **Short & Factual**: Convey what happened or what action to take.
- **Sentence Case**: Use sentence case for buttons, labels, and headings (e.g. "Find keywords", "Target market", "Copy all").
- **Zero Exclamation Marks**: Never use exclamation marks in product UI copy.
- **No Personification**: Avoid "I'm thinking", "I have found". Use "Analyzing brief", "Generated 20 keywords".

## Step-by-step procedure

1. **Verify Tokens**: Ensure all CSS variable tokens in `resources/design-tokens.md` are mapped in `tailwind.config.js`.
2. **Apply Typography**: Verify Inter Variable is applied to `body` and JetBrains Mono Variable is applied to `code`, `pre`, and keyword chips.
3. **Execute Design Review Checklist**: Inspect spacing, contrast, borders, and dark mode against `resources/ui-review-checklist.md`.

## Rules (do / don't)
- **DO** use 1px borders to establish depth and hierarchy.
- **DO** enforce 13px base body text for high operational density.
- **DO** pair any colored status indicator with text or icon.
- **DON'T** use gradient backgrounds, glow filters, or glassmorphic blur effects.
- **DON'T** use conversational AI filler in UI notifications.

## Examples
See `resources/design-tokens.md` for exact hex tokens and `resources/ui-review-checklist.md` for the quality assurance audit list.

## Checklist before finishing
- [ ] No gradient hero text, glow shadows, or glassmorphism in stylesheet.
- [ ] All icons use `lucide-react` at 16px with stroke 1.5.
- [ ] Spacing values adhere to 4px multiples.
- [ ] Base text is 13px Inter; chips and codes are JetBrains Mono.
- [ ] Sentence case applied across all UI copy with zero exclamation marks.
- [ ] Light and dark themes audited against `resources/ui-review-checklist.md`.
