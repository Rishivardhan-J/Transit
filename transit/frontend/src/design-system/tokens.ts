/**
 * Command Navy design tokens (PRD 11.1) - the single source for Tailwind, charts and the map.
 * 60-30-10: dominant #0F172A, secondary #1E293B, accent #F59E0B.
 */
export const colors = {
  surface: { dominant: '#0F172A', secondary: '#1E293B' },
  accent: '#F59E0B',
  text: { primary: '#F1F5F9', secondary: '#94A3B8', muted: '#64748B' },
  border: { default: '#334155', hover: '#475569' },
  status: {
    success: { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ADE80' },
    warning: { bg: 'rgba(245, 158, 11, 0.18)', text: '#FCD34D' },
    error: { bg: 'rgba(239, 68, 68, 0.15)', text: '#FCA5A5' },
  },
} as const

/**
 * Categorical colours for vehicles/series. None of them is green, amber-warning or red, so vehicle
 * identity can never be mistaken for status (PRD 11.1). Beyond 8 vehicles colours repeat with a dashed line.
 */
export const catColors = [
  '#38BDF8', // sky
  '#A78BFA', // violet
  '#F472B6', // pink
  '#22D3EE', // cyan
  '#818CF8', // indigo
  '#E879F9', // fuchsia
  '#E2C799', // sand
  '#7DD3FC', // light sky
] as const

export type PlanStatus = 'on_time' | 'at_risk' | 'late' | 'unassigned' | 'pending'

/** Status -> map/chart colour (the `text` tone of the badge palette) and the glyph that accompanies it. */
export const statusStyle: Record<PlanStatus, { color: string; glyph: string; label: string }> = {
  on_time: { color: colors.status.success.text, glyph: '✓', label: 'On time' },
  at_risk: { color: colors.status.warning.text, glyph: '!', label: 'At risk' },
  late: { color: colors.status.error.text, glyph: '✕', label: 'Late' },
  unassigned: { color: colors.text.secondary, glyph: '?', label: 'Unassigned' },
  pending: { color: colors.text.muted, glyph: '•', label: 'Upcoming' },
}

export const vehicleColor = (i: number) => catColors[i % catColors.length]
export const vehicleDashed = (i: number) => i >= catColors.length
