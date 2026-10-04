# Design Tokens: Marketplace Keyword Agent

A restrained, high-clarity design system engineered for fast scanning, zero clutter, and utility-first information density.

---

## 1. Color Palette

The interface uses a deliberate, quiet neutral foundation with crisp semantic accents. No garish gradients or distracting marketing banners.

### Neutrals (Slate / Zinc)
- **Background App**: `#0f172a` (Slate 900 - Dark mode default) / `#f8fafc` (Slate 50 - Light mode surface)
- **Card Surface**: `#1e293b` (Slate 800) / `#ffffff` (Pure white)
- **Card Border**: `#334155` (Slate 700) / `#e2e8f0` (Slate 200)
- **Text Primary**: `#f8fafc` (Slate 50) / `#0f172a` (Slate 900)
- **Text Secondary**: `#94a3b8` (Slate 400) / `#64748b` (Slate 500)
- **Text Muted**: `#64748b` (Slate 500) / `#94a3b8` (Slate 400)

### Platform Accent Badges
- **Amazon**:
  - Badge Background: `#451a03` (Dark Amber tint) / `#fef3c7`
  - Badge Border: `#d97706` (Amber 600)
  - Badge Text: `#fbbf24` (Amber 400) / `#92400e`
- **Myntra**:
  - Badge Background: `#500724` (Dark Rose tint) / `#ffe4e6`
  - Badge Border: `#e11d48` (Rose 600)
  - Badge Text: `#fb7185` (Rose 400) / `#9f1239`
- **Flipkart**:
  - Badge Background: `#172554` (Dark Blue tint) / `#dbeafe`
  - Badge Border: `#2563eb` (Blue 600)
  - Badge Text: `#60a5fa` (Blue 400) / `#1e40af`

### Status & Feedback
- **Active / Running**: `#38bdf8` (Sky 400)
- **Success / Completed**: `#4ade80` (Emerald 400)
- **Warning / Blocked**: `#fbbf24` (Amber 400)
- **Error**: `#f87171` (Red 400)

---

## 2. Typography Scale

- **Font Family**: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
- **Font Sizes**:
  - `xs`: 0.75rem (12px) - Chip counts, timestamps, badges
  - `sm`: 0.875rem (14px) - Keyword chips, form inputs, secondary labels
  - `base`: 1.0rem (16px) - Body copy, chat messages
  - `lg`: 1.125rem (18px) - Section headers, card titles
  - `xl`: 1.25rem (20px) - App header title

---

## 3. Spacing & Radius Scale

- **Component Spacing**:
  - Chips gap: `gap-1.5` (6px) or `gap-2` (8px)
  - Section margin: `mb-6` (24px)
  - Card padding: `p-5` (20px)
- **Border Radius**:
  - Keyword Chips: `rounded-md` (6px)
  - Cards & Modals: `rounded-xl` (12px)
  - Form Inputs: `rounded-lg` (8px)
  - Buttons: `rounded-lg` (8px)

---

## 4. Keyword Chip Style Specification

Keyword chips are strictly plain text badges designed for rapid copy-and-paste.
- **Padding**: `px-2.5 py-1`
- **Font**: `text-xs md:text-sm font-medium`
- **Background**: `bg-slate-800/80 hover:bg-slate-700`
- **Border**: `border border-slate-700/60`
- **Hover**: Cursor pointer, visual copy tooltip or checkmark flash on click.
- **Forbidden**: No percentage numbers, no search volume numbers, no popularity bars.
