export const fmtNum = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 })

export const fmtPct = (v: number | null | undefined, digits = 1) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${fmtNum(v, digits)}%`)

export const fmtTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'

export const fmtDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

export const fmtDelta = (v: number | undefined, digits = 1) => (v === undefined ? '—' : `${v > 0 ? '+' : ''}${fmtNum(v, digits)}`)
