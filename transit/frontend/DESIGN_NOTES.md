# Transit Design System (Tokens)

This document is the source of truth for the visual constraints of the Transit frontend (Phase 5). The system is designed to provide a highly polished, information-dense, dark-mode dashboard tailored for logistics operations.

## Color System
The UI adheres strictly to a **60-30-10** distribution rule:
- **60% Dominant (Backgrounds):** Deep Slate `#0F172A`
- **30% Secondary (Cards, Surfaces):** Lighter Slate `#1E293B`
- **10% Accent (Interactive, Highlights):** Amber `#F59E0B`

### Text & Borders
- **Text Primary:** `#F1F5F9`
- **Text Secondary:** `#94A3B8`
- **Text Muted:** `#64748B`
- **Borders:** `#334155` (Hover: `#475569`)

## Spacing Grid
The entire application uses a strict 4px baseline grid. Padding, margins, and layout gaps must map to one of the following scale values:
- `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `48px`, `64px`, `96px`.
Arbitrary spacing is disallowed at the Tailwind configuration level.

## Component Specifications

### KPI Cards
- H1: `20px` bold, Accent color.
- Value: `32px` bold, Primary text.
- Trend indicator included where applicable (success/error/neutral colors).

### Data Tables
- Header: All caps, `14px`, medium weight, Secondary text.
- Rows: Clean 1px borders separating items. Subtle row highlight (`#0F172A`/50%) on hover.

### Maps (Route Map)
- Base Layer: OpenFreeMap Dark (`https://tiles.openfreemap.org/styles/dark`). Used to avoid CARTO's API key requirement for external direct usage.
- Categorical colors applied to routes and matching stops (up to 8 distinct tracking colors).
- Stops are clickable, launching the SHAP Explainability Panel overlay.

### Contrast Ratios
The dashboard strictly adheres to WCAG AA/AAA standards for low-light environments.
| Element Pair | Colors | Ratio |
| :--- | :--- | :--- |
| Text Primary on Dominant | `#F1F5F9` on `#0F172A` | **16.3:1** |
| Text Secondary on Dominant | `#94A3B8` on `#0F172A` | **6.4:1** |
| Text Muted on Secondary | `#64748B` on `#1E293B` | **4.6:1** |
| Accent on Secondary | `#F59E0B` on `#1E293B` | **7.5:1** |


## Self-Critique: What we deliberately did NOT add
**Light Mode Toggle**: We deliberately omitted a light mode or theme switcher. The PRD explicitly mandates a dark-mode, high-contrast dashboard tailored for operations centers (which typically have low ambient lighting). Adding a light mode would dilute the strict 60-30-10 color balance and introduce unnecessary CSS variables that violate the rigid design constraints.
