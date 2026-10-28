import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { api } from '../api/endpoints'
import type { WhatIfResponse } from '../api/types'
import { MapCanvas } from '../map/MapCanvas'
import { MetricsCompare } from '../components/PlanSummary'
import { Button, Card, CardHeader, Heading, Skeleton, Slider, StatusBadge, Text, errorMessage, toast } from '../components/ui'
import { PRESETS, setWeight, WEIGHT_KEYS, type WeightKey, type WeightMap } from '../lib/weights'
import { fmtNum } from '../lib/format'

const LABELS: Record<WeightKey, { label: string; hint: string }> = {
  w_distance: { label: 'Distance', hint: 'Shorter routes' },
  w_time: { label: 'Time', hint: 'Predicted travel time' },
  w_fuel: { label: 'Fuel', hint: 'Fuel cost per vehicle efficiency' },
  w_delay: { label: 'Delay', hint: 'Protect urgent and tight windows' },
}
const DEBOUNCE_MS = 400

export function WhatIf() {
  const qc = useQueryClient()
  const [weights, setWeights] = useState<WeightMap>(PRESETS.balanced)
  const [result, setResult] = useState<WhatIfResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)
  const seq = useRef(0)

  const solve = useCallback(async (w: WeightMap) => {
    const mine = ++seq.current   // only the latest request may update the screen
    setBusy(true); setError(null)
    try {
      const r = await api.whatIf(w, { max_runtime_s: 4 })
      if (mine === seq.current) setResult(r)
    } catch (e) {
      if (mine === seq.current) setError(errorMessage(e))
    } finally { if (mine === seq.current) setBusy(false) }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => { void solve(weights) }, DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [weights, solve])

  const apply = async () => {
    setApplying(true)
    try {
      await api.whatIf(weights, { commit: true, max_runtime_s: 8 })
      await qc.invalidateQueries()
      toast('success', 'Plan applied. Dashboard and map now show these routes.')
    } catch (e) { toast('error', errorMessage(e)) } finally { setApplying(false) }
  }

  const sum = WEIGHT_KEYS.reduce((s, k) => s + weights[k], 0)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Heading level={1} size={32}>What-if sandbox</Heading>
        <Text variant="secondary" className="mt-1">Move a slider and the router re-solves the current orders under the new priorities. Weights always sum to 100%.</Text>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <Card className="xl:col-span-3 h-fit">
          <CardHeader title="Cost weights" description={`Total ${fmtNum(sum * 100, 0)}%`} />
          <div className="p-4 flex flex-col gap-6">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Presets">
              {Object.keys(PRESETS).map((p) => (
                <Button key={p} variant="outline" className="h-8 px-3 text-12" onClick={() => setWeights(PRESETS[p])}>{p.replace('_', ' ')}</Button>
              ))}
            </div>
            {WEIGHT_KEYS.map((k) => (
              <div key={k} className="flex flex-col gap-1">
                <Slider label={LABELS[k].label} value={weights[k]} onChange={(v) => setWeights((w) => setWeight(w, k, v))} format={(v) => `${Math.round(v * 100)}%`} />
                <Text variant="secondary" size={12}>{LABELS[k].hint}</Text>
              </div>
            ))}
            <Button onClick={apply} loading={applying} disabled={!result || busy} icon={<CheckCircle2 className="h-icon w-icon" aria-hidden />}>Apply this plan</Button>
          </div>
        </Card>

        <div className="xl:col-span-6 flex flex-col gap-3">
          <div aria-live="polite" className="h-8 flex items-center">
            {busy ? <StatusBadge tone="neutral" label="Re-solving…" /> : error ? <StatusBadge tone="error" label={error} /> : result ? <StatusBadge tone="success" label={`Solved in ${fmtNum(result.metrics.runtime_s, 1)} s`} /> : null}
          </div>
          {result ? <MapCanvas plan={result.plan} animate className="h-map-lg" /> : <Skeleton className="h-map-lg w-full" />}
        </div>

        <Card className="xl:col-span-3 h-fit">
          <CardHeader title="Change vs current plan" description={result?.current_metrics ? 'Green = better, amber = worse' : 'No current plan to compare'} />
          <div className="px-4">{result ? <MetricsCompare current={result.current_metrics} next={result.metrics} delta={result.delta_vs_current} /> : <Skeleton className="h-chart my-4" />}</div>
        </Card>
      </div>
    </div>
  )
}
