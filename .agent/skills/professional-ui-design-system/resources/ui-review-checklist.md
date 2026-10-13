# UI Review Checklist: Product Engineering Standards

This checklist is used to inspect all visual implementations before declaring UI tasks complete.

---

## 1. Visual Alignment & Grid
- [ ] Every element's padding, margin, gap, and dimension is an exact multiple of 4px.
- [ ] No element exceeds `rounded-lg` (8px radius) unless it is a circular status badge or avatar.
- [ ] 1px subtle borders (`border-border`) are used instead of layered blur drop shadows.
- [ ] Icons are strictly 16px with 1.5 stroke width (`lucide-react`).
- [ ] No gradient text, radial orbs, glowing halos, or glassmorphic blur filters exist.

---

## 2. Typography & Hierarchy
- [ ] Base text is 13px Inter Variable; technical values and keywords use JetBrains Mono Variable.
- [ ] Contrast ratio between text and its immediate background is at least 4.5:1 (WCAG AA).
- [ ] Long keywords or labels wrap or truncate gracefully with an ellipsis (`truncate` or `break-words`).
- [ ] Text hierarchy relies on weight (`font-medium`, `font-semibold`) and color mutedness, not drastic font size jumps.
- [ ] Headings and buttons use sentence case; zero exclamation marks appear in UI copy.

---

## 3. Interactive States
- [ ] **Hover**: Buttons, chips, and table rows have subtle, deterministic background/border shifts.
- [ ] **Focus**: All interactive elements display a visible, high-contrast focus ring (`focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:outline-none`).
- [ ] **Active / Pressed**: Subtle scale or background darkening confirms user click.
- [ ] **Disabled**: Low opacity (`opacity-50`) with `pointer-events-none` and appropriate `aria-disabled="true"`.

---

## 4. Theme Integrity (Light & Dark)
- [ ] Tested and verified in dark mode (`class="dark"` or prefers-color-scheme dark).
- [ ] Tested and verified in light mode (`class="light"` or prefers-color-scheme light).
- [ ] Backgrounds never use pure unstyled black (`#000000`) or blinding flat white without borders; graphite tokens are maintained.
- [ ] Status indicators (success emerald, warning amber, error rose) are clearly legible in both themes.

---

## 5. Viewports & Responsiveness
- [ ] Tested at **1440 × 900** (standard desktop): canvas controls, drawer, and forms render without overlap.
- [ ] Tested at **1024 × 768** (tablet / compact laptop): canvas scales and pans smoothly; drawer does not clip controls.
- [ ] MiniMap and zoom controls reposition gracefully when the right-side drawer is expanded.
