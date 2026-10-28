import { useEffect, useState } from 'react'
import { Play } from 'lucide-react'
import { useOptimizationJob } from '../hooks/useOptimizationJob'
import { PRESETS } from '../lib/weights'
import { Button, Modal, Slider, StatusBadge, Text, toast } from './ui'
import { fmtNum } from '../lib/format'

const SOLVERS = [
  { id: 'hgs', label: 'HGS (recommended)' },
  { id: 'ortools', label: 'Google OR-Tools' },
  { id: 'nn', label: 'Nearest neighbour' },
]

export function RunOptimizationModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { job, start, reset, channel } = useOptimizationJob()
  const [solver, setSolver] = useState('hgs')
  const [preset, setPreset] = useState('balanced')
  const [risk, setRisk] = useState(0.25)
  const running = job.status === 'running'

  useEffect(() => {
    if (job.status === 'completed') toast('success', 'Plan ready: routes and predictions are up to date.')
    if (job.status === 'failed') toast('error', job.error ?? 'Optimization failed')
  }, [job.status, job.error])

  const close = () => { if (!running) { reset(); onClose() } }

  return (
    <Modal open={open} onClose={close} title="Run optimization">
      <div className="flex flex-col gap-4">
        <label className="flex flex-col gap-2 text-14 font-medium">
          Solver
          <select value={solver} disabled={running} onChange={(e) => setSolver(e.target.value)}
            className="h-control-h bg-surface-dominant border-1 border-border-default rounded-md px-3 text-14 font-normal">
            {SOLVERS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-2 text-14 font-medium">
          Cost preset
          <select value={preset} disabled={running} onChange={(e) => setPreset(e.target.value)}
            className="h-control-h bg-surface-dominant border-1 border-border-default rounded-md px-3 text-14 font-normal">
            {Object.keys(PRESETS).map((p) => <option key={p} value={p}>{p.replace('_', ' ')}</option>)}
          </select>
        </label>
        <Slider label="Planning caution (0 = median travel time, 1 = p90)" value={risk} onChange={setRisk} disabled={running} />

        {job.status !== 'idle' && (
          <div className="flex flex-col gap-2" aria-live="polite">
            <div className="h-2 bg-surface-dominant rounded-full overflow-hidden" role="progressbar" aria-valuenow={job.progress} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full bg-accent transition-all duration-150" style={{ width: `${job.progress}%` }} />
            </div>
            <div className="flex items-center justify-between">
              <Text variant="secondary" size={12}>{job.stage || 'starting'}</Text>
              <Text variant="muted" size={12}>{channel === 'live' ? 'live updates' : channel === 'polling' ? 'polling' : ''}</Text>
            </div>
            {job.status === 'completed' && job.result && (
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge tone="success" label={`${job.result.routes} routes`} />
                <StatusBadge tone={Number(job.result.unassigned) ? 'warning' : 'success'} label={`${job.result.unassigned} unassigned`} />
                <StatusBadge tone={Number(job.result.predicted_late) ? 'warning' : 'success'} label={`${job.result.predicted_late} at risk`} />
                <Text variant="secondary" size={12}>distance {fmtNum(Number(job.result.total_distance))}</Text>
              </div>
            )}
            {job.status === 'failed' && <StatusBadge tone="error" label={job.error ?? 'Failed'} />}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={close} disabled={running}>{job.status === 'completed' ? 'Close' : 'Cancel'}</Button>
          <Button icon={<Play className="h-icon w-icon" aria-hidden />} loading={running}
            onClick={() => start({ solver_type: solver, weight_config: { preset }, risk_lambda: risk, max_runtime_s: 20 })}>
            {job.status === 'completed' ? 'Run again' : 'Start'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
