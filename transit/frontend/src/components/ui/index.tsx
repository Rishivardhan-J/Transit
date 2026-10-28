import React, { useEffect, useId, useRef } from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { AlertTriangle, CheckCircle2, CircleHelp, Inbox, Loader2, Minus, X, XCircle } from 'lucide-react'
import type { PlanStatus } from '../../design-system/tokens'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/* ----------------------------------------------------------------- typography */
type TextVariant = 'primary' | 'secondary' | 'muted'
const variantClass: Record<TextVariant, string> = { primary: 'text-text-primary', secondary: 'text-text-secondary', muted: 'text-text-muted' }
const sizeClass = { 12: 'text-12', 14: 'text-14', 16: 'text-16', 20: 'text-20', 24: 'text-24', 32: 'text-32', 48: 'text-48' } as const
const weightClass = { normal: 'font-normal', medium: 'font-medium', semibold: 'font-semibold', bold: 'font-bold' } as const

export function Text({ variant = 'primary', size = 14, weight = 'normal', as: Tag = 'p', className, ...props }:
  React.HTMLAttributes<HTMLElement> & { variant?: TextVariant; size?: keyof typeof sizeClass; weight?: keyof typeof weightClass; as?: React.ElementType }) {
  return <Tag className={cn(variantClass[variant], sizeClass[size], weightClass[weight], className)} {...props} />
}

export function Heading({ level = 2, size = 24, weight = 'semibold', className, ...props }:
  React.HTMLAttributes<HTMLHeadingElement> & { level?: 1 | 2 | 3 | 4; size?: 16 | 20 | 24 | 32 | 48; weight?: 'medium' | 'semibold' | 'bold' }) {
  const Tag = `h${level}` as React.ElementType
  return <Tag className={cn('text-text-primary', sizeClass[size], weightClass[weight], className)} {...props} />
}

/* ----------------------------------------------------------------- surfaces */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('bg-surface-secondary border-1 border-border-default rounded-md flex flex-col', className)} {...props} />
}

export function CardHeader({ title, description, actions, className }:
  { title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-start justify-between gap-4 p-4 border-b-1 border-border-default', className)}>
      <div className="min-w-0">
        <Heading level={3} size={16}>{title}</Heading>
        {description && <Text variant="secondary" size={12} className="mt-1">{description}</Text>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

/* ----------------------------------------------------------------- buttons */
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost'
const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-surface-dominant hover:opacity-80',
  secondary: 'bg-surface-dominant text-text-primary border-1 border-border-default hover:border-border-hover',
  outline: 'border-1 border-border-default text-text-primary hover:border-border-hover',
  ghost: 'text-text-secondary hover:text-text-primary',
}

export const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean; icon?: React.ReactNode }>(
  ({ className, variant = 'primary', loading, icon, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 h-control-h px-4 rounded-md text-14 font-medium transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none',
        buttonVariants[variant], className,
      )}
      {...props}
    >
      {loading ? <Loader2 className="h-icon w-icon animate-spin" aria-hidden /> : icon}
      {children}
    </button>
  ),
)
Button.displayName = 'Button'

/** Icon-only button: the accessible name is mandatory. */
export const IconButton = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { 'aria-label': string }>(
  ({ className, ...props }, ref) => (
    <button
      ref={ref}
      className={cn('inline-flex items-center justify-center h-control-h w-control-h rounded-md text-text-secondary hover:text-text-primary hover:bg-surface-dominant transition-colors duration-150', className)}
      {...props}
    />
  ),
)
IconButton.displayName = 'IconButton'

/* ----------------------------------------------------------------- status */
const badgeStyle = {
  success: 'bg-status-success-bg text-status-success-text',
  warning: 'bg-status-warning-bg text-status-warning-text',
  error: 'bg-status-error-bg text-status-error-text',
  neutral: 'bg-surface-dominant text-text-secondary border-1 border-border-default',
} as const
type BadgeTone = keyof typeof badgeStyle
const badgeIcon = { success: CheckCircle2, warning: AlertTriangle, error: XCircle, neutral: Minus } as const

/** Status is never colour alone: every badge carries an icon and text. */
export function StatusBadge({ tone, label, className }: { tone: BadgeTone; label: string; className?: string }) {
  const Icon = badgeIcon[tone]
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-1 rounded-full text-12 font-medium', badgeStyle[tone], className)}>
      <Icon className="h-icon w-icon" aria-hidden />
      {label}
    </span>
  )
}

export const planStatusTone: Record<PlanStatus, BadgeTone> = { on_time: 'success', at_risk: 'warning', late: 'error', unassigned: 'neutral', pending: 'neutral' }
export const planStatusLabel: Record<PlanStatus, string> = { on_time: 'On time', at_risk: 'At risk', late: 'Late', unassigned: 'Unassigned', pending: 'Upcoming' }
export const PlanStatusBadge = ({ status }: { status: PlanStatus }) => <StatusBadge tone={planStatusTone[status]} label={planStatusLabel[status]} />

/* ----------------------------------------------------------------- feedback states */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('bg-surface-dominant rounded-md animate-pulse', className)} />
}

export function EmptyState({ icon: Icon = Inbox, title, description, action, className }:
  { icon?: React.ElementType; title: string; description?: React.ReactNode; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-start justify-center gap-3 p-6', className)}>
      <Icon className="h-icon-lg w-icon-lg text-text-muted" aria-hidden />
      <div>
        <Text weight="medium">{title}</Text>
        {description && <Text variant="secondary" size={12} className="mt-1 max-w-panel-md">{description}</Text>}
      </div>
      {action}
    </div>
  )
}

export function ErrorState({ error, onRetry, title = 'Something went wrong' }: { error: unknown; onRetry?: () => void; title?: string }) {
  const detail = errorMessage(error)
  return (
    <div role="alert" className="flex flex-col items-start gap-3 p-6">
      <AlertTriangle className="h-icon-lg w-icon-lg text-status-error-text" aria-hidden />
      <div>
        <Text weight="medium">{title}</Text>
        <Text variant="secondary" size={12} className="mt-1 max-w-panel-md">{detail}</Text>
      </div>
      {onRetry && <Button variant="outline" onClick={onRetry}>Try again</Button>}
    </div>
  )
}

export function errorMessage(error: unknown): string {
  const e = error as { response?: { data?: { detail?: unknown } ; status?: number }; message?: string }
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x: { msg?: string }) => x.msg ?? JSON.stringify(x)).join('; ')
  if (e?.response?.status === 403) return 'Your role does not have access to this.'
  if (e?.response?.status === 503) return 'The model service is unavailable. Train a model first.'
  return e?.message ?? 'Unexpected error'
}

/** Shows skeleton / error / empty / content for a react-query result. */
export function QueryBoundary<T>({ query, children, skeleton, empty }:
  { query: { data?: T; isLoading: boolean; error: unknown; refetch: () => unknown }; children: (data: T) => React.ReactNode; skeleton?: React.ReactNode; empty?: (data: T) => boolean }) {
  if (query.isLoading) return <>{skeleton ?? <Skeleton className="h-chart w-full" />}</>
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  if (query.data === undefined || (empty && empty(query.data))) return <EmptyState title="Nothing to show yet" />
  return <>{children(query.data)}</>
}

/* ----------------------------------------------------------------- stat */
export function Stat({ label, value, hint, tone, className }:
  { label: string; value: React.ReactNode; hint?: React.ReactNode; tone?: BadgeTone; className?: string }) {
  return (
    <Card className={cn('p-4 gap-2', className)}>
      <Text variant="secondary" size={12} weight="medium" className="uppercase tracking-wide">{label}</Text>
      <Text size={32} weight="bold" className="leading-none">{value}</Text>
      {hint && (tone ? <StatusBadge tone={tone} label={String(hint)} className="self-start" /> : <Text variant="muted" size={12}>{hint}</Text>)}
    </Card>
  )
}

/* ----------------------------------------------------------------- form controls */
export function Switch({ checked, onChange, label, className }: { checked: boolean; onChange: (v: boolean) => void; label: string; className?: string }) {
  return (
    <button
      type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
      className={cn('relative inline-flex h-toggle-h w-toggle shrink-0 items-center rounded-full transition-colors duration-150', checked ? 'bg-accent' : 'bg-border-hover', className)}
    >
      <span className={cn('inline-block h-knob w-knob rounded-full bg-text-primary transition-transform duration-150', checked ? 'translate-x-4 ml-1' : 'translate-x-0 ml-1')} />
    </button>
  )
}

export function Slider({ label, value, onChange, min = 0, max = 1, step = 0.01, format, disabled }:
  { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number; format?: (v: number) => string; disabled?: boolean }) {
  const id = useId()
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-14 font-medium text-text-primary">{label}</label>
        <span className="text-14 text-accent font-semibold tabular-nums">{format ? format(value) : value.toFixed(2)}</span>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-accent" />
    </div>
  )
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div role="tablist" className="inline-flex gap-1 p-1 bg-surface-dominant border-1 border-border-default rounded-md">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cn('px-3 py-1 rounded-sm text-14 font-medium transition-colors duration-150', value === t.id ? 'bg-accent text-surface-dominant' : 'text-text-secondary hover:text-text-primary')}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

/* ----------------------------------------------------------------- drawer & modal */
function useFocusTrap(open: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const prev = document.activeElement as HTMLElement | null
    const node = ref.current
    const focusables = () => Array.from(node?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])') ?? []).filter((el) => !el.hasAttribute('disabled'))
    focusables()[0]?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'Tab') {
        const f = focusables()
        if (!f.length) return
        const first = f[0], last = f[f.length - 1]
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); prev?.focus() }
  }, [open, onClose])
  return ref
}

export function Drawer({ open, onClose, title, children, side = 'right', className }:
  { open: boolean; onClose: () => void; title: string; children: React.ReactNode; side?: 'right' | 'left'; className?: string }) {
  const ref = useFocusTrap(open, onClose)
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-surface-dominant/80" onClick={onClose} aria-hidden />
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={cn('absolute top-0 h-full w-panel-md max-w-full bg-surface-secondary border-border-default flex flex-col', side === 'right' ? 'right-0 border-l-1' : 'left-0 border-r-1', className)}>
        <div className="flex items-center justify-between p-4 border-b-1 border-border-default">
          <Heading level={2} size={16}>{title}</Heading>
          <IconButton aria-label="Close" onClick={onClose}><X className="h-icon w-icon" aria-hidden /></IconButton>
        </div>
        <div className="flex-1 overflow-auto">{children}</div>
      </div>
    </div>
  )
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  const ref = useFocusTrap(open, onClose)
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-surface-dominant/80" onClick={onClose} aria-hidden />
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title} className="relative w-panel-lg max-w-full bg-surface-secondary border-1 border-border-default rounded-md">
        <div className="flex items-center justify-between p-4 border-b-1 border-border-default">
          <Heading level={2} size={16}>{title}</Heading>
          <IconButton aria-label="Close" onClick={onClose}><X className="h-icon w-icon" aria-hidden /></IconButton>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  )
}

/* ----------------------------------------------------------------- table */
export interface Column<T> { key: string; header: string; numeric?: boolean; render?: (row: T) => React.ReactNode }

/** Left-aligned text, right-aligned tabular numbers (PRD 11.2). Scrolls horizontally inside its own card only. */
export function DataTable<T extends object>({ columns, data, rowKey, onRowClick, empty }:
  { columns: Column<T>[]; data: T[]; rowKey?: (row: T, i: number) => string; onRowClick?: (row: T) => void; empty?: string }) {
  if (!data.length) return <EmptyState title={empty ?? 'No rows'} />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-14">
        <thead>
          <tr className="border-b-1 border-border-default">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={cn('px-4 py-2 text-12 font-medium uppercase tracking-wide text-text-secondary whitespace-nowrap', c.numeric ? 'text-right' : 'text-left')}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={rowKey ? rowKey(row, i) : i} onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn('border-b-1 border-border-default last:border-b-0 hover:bg-surface-dominant/50', onRowClick && 'cursor-pointer')}>
              {columns.map((c) => (
                <td key={c.key} className={cn('px-4 py-2 whitespace-nowrap', c.numeric ? 'text-right tabular-nums' : 'text-left')}>
                  {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ----------------------------------------------------------------- toast */
export interface ToastItem { id: number; tone: 'success' | 'error' | 'info'; text: string }
type Listener = (t: ToastItem[]) => void
let toasts: ToastItem[] = []
const listeners = new Set<Listener>()
let seq = 0
export const toast = (tone: ToastItem['tone'], text: string) => {
  const item = { id: ++seq, tone, text }
  toasts = [...toasts, item]
  listeners.forEach((l) => l(toasts))
  setTimeout(() => { toasts = toasts.filter((t) => t.id !== item.id); listeners.forEach((l) => l(toasts)) }, 5000)
}
export function Toaster() {
  const [items, setItems] = React.useState<ToastItem[]>(toasts)
  useEffect(() => { listeners.add(setItems); return () => { listeners.delete(setItems) } }, [])
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className="bg-surface-secondary border-1 border-border-default rounded-md p-3 flex items-center gap-2 max-w-panel-md">
          {t.tone === 'success' ? <CheckCircle2 className="h-icon w-icon text-status-success-text" aria-hidden /> : t.tone === 'error' ? <XCircle className="h-icon w-icon text-status-error-text" aria-hidden /> : <CircleHelp className="h-icon w-icon text-text-secondary" aria-hidden />}
          <Text size={14}>{t.text}</Text>
        </div>
      ))}
    </div>
  )
}
