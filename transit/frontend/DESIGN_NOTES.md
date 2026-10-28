# Transit design system (Command Navy)

Source of truth: `src/design-system/tokens.ts`, consumed by `tailwind.config.ts`, charts and the map. Tailwind's defaults are removed (`theme`, not `theme.extend`), so a value off the 4px grid or type scale does not exist. Layout sizes that are not spacing steps are *named* (`panel-md`, `chart`, `map-lg`, `control-h`, ...).

* 60-30-10: `#0F172A` / `#1E293B` / accent `#F59E0B`. Text `#F1F5F9` `#94A3B8` `#64748B`, border `#334155` (hover `#475569`).
* Status colours are fixed and always paired with an icon and text (`StatusBadge`, map glyphs ✓ ! ✕ ? •).
* Eight categorical vehicle colours, none green/amber/red; beyond 8 vehicles lines repeat dashed.
* Inter 400/500 (+600/700 for numbers), scale 12/14/16/20/24/32/48, tabular numerals; Lucide icons only; max content width 1536px.
* Motion ≤150ms for UI state; route morph (600ms) is data animation and is disabled under `prefers-reduced-motion`.

## Contrast (computed, `make contrast`)

Primary/secondary text and accent pass AA on both surfaces (5.7–16.3:1); status badges 6.5–7.3:1. **Muted text `#64748B` fails AA** (3.75:1 on #0F172A, 3.07:1 on #1E293B), so it is used for icons only. The earlier doc's "7.5:1 for accent on secondary" was wrong: it is 6.81:1.

## Deliberately not built

Light theme (PRD: dark only for v1).
