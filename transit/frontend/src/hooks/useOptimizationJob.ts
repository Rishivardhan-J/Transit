import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api/endpoints'
import { wsUrl } from '../api/client'
import { errorMessage } from '../components/ui'
import { useLiveChannel } from './useLiveChannel'

export interface JobMessage { job_id: string; status: string; stage?: string; progress?: number; result?: Record<string, unknown> }
export interface JobState { jobId: string | null; status: 'idle' | 'running' | 'completed' | 'failed'; stage: string; progress: number; error?: string; result?: Record<string, unknown> }
const IDLE: JobState = { jobId: null, status: 'idle', stage: '', progress: 0 }

/** Starts a Celery job and follows it over WebSocket (REST polling as fallback); refreshes plan data when it finishes. */
export function useOptimizationJob() {
  const qc = useQueryClient()
  const [job, setJob] = useState<JobState>(IDLE)

  const finish = useCallback((next: Partial<JobState>) => {
    setJob((j) => ({ ...j, ...next }))
    if (next.status === 'completed') void qc.invalidateQueries()
  }, [qc])

  const live = useLiveChannel<JobMessage>({
    url: job.jobId && job.status === 'running' ? wsUrl(`/ws/jobs/${job.jobId}`) : null,
    onMessage: (m) => {
      if (m.status === 'completed') finish({ status: 'completed', progress: 100, stage: 'done', result: m.result })
      else if (m.status === 'failed') finish({ status: 'failed', error: String(m.result?.error ?? 'Optimization failed') })
      else setJob((j) => ({ ...j, stage: m.stage ?? j.stage, progress: m.progress ?? j.progress }))
    },
    isFinal: (m) => m.status === 'completed' || m.status === 'failed',
    poll: async () => {
      if (!job.jobId) return
      const s = await api.job(job.jobId)
      if (s.status === 'completed') finish({ status: 'completed', progress: 100, stage: 'done' })
      else if (s.status === 'failed') finish({ status: 'failed', error: s.error ?? 'Optimization failed' })
    },
  })

  const start = useCallback(async (body: Parameters<typeof api.optimize>[0]) => {
    setJob({ jobId: null, status: 'running', stage: 'queued', progress: 0 })
    try {
      const { job_id } = await api.optimize(body)
      setJob({ jobId: job_id, status: 'running', stage: 'queued', progress: 2 })
    } catch (e) {
      setJob({ jobId: null, status: 'failed', stage: '', progress: 0, error: errorMessage(e) })
    }
  }, [])

  return { job, start, reset: () => setJob(IDLE), channel: live }
}
