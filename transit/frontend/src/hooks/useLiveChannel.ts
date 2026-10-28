import { useEffect, useRef, useState } from 'react'

export type LiveState = 'connecting' | 'live' | 'polling' | 'off'

interface Options<T> {
  /** WebSocket URL, or null to stay disconnected. */
  url: string | null
  onMessage: (msg: T) => void
  /** Called every `pollMs` while the socket is down (the REST fallback described in the Phase 4 notes). */
  poll?: () => void | Promise<void>
  pollMs?: number
  /** Message predicate that closes the channel for good (e.g. job completed). */
  isFinal?: (msg: T) => boolean
}

/**
 * WebSocket subscription that reconnects with exponential backoff and falls back to polling while disconnected,
 * so a Redis restart or dropped socket never leaves the UI frozen.
 */
export function useLiveChannel<T = unknown>({ url, onMessage, poll, pollMs = 3000, isFinal }: Options<T>): LiveState {
  const [state, setState] = useState<LiveState>(url ? 'connecting' : 'off')
  const handlers = useRef({ onMessage, poll, isFinal })
  handlers.current = { onMessage, poll, isFinal }

  useEffect(() => {
    if (!url) { setState('off'); return }
    let ws: WebSocket | null = null
    let retry = 0
    let closed = false
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let pollTimer: ReturnType<typeof setInterval> | undefined

    const stopPolling = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = undefined } }
    const startPolling = () => {
      if (pollTimer || !handlers.current.poll) return
      setState('polling')
      pollTimer = setInterval(() => { void handlers.current.poll?.() }, pollMs)
    }

    const connect = () => {
      if (closed) return
      setState('connecting')
      try { ws = new WebSocket(url) } catch { startPolling(); return }
      ws.onopen = () => { retry = 0; stopPolling(); setState('live') }
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as T
          handlers.current.onMessage(msg)
          if (handlers.current.isFinal?.(msg)) { closed = true; ws?.close(); setState('off') }
        } catch { /* ignore malformed frames */ }
      }
      ws.onclose = () => {
        if (closed) return
        startPolling()
        const delay = Math.min(15000, 1000 * 2 ** retry++)
        reconnectTimer = setTimeout(connect, delay)
      }
      ws.onerror = () => ws?.close()
    }
    connect()
    return () => { closed = true; clearTimeout(reconnectTimer); stopPolling(); ws?.close() }
  }, [url, pollMs])

  return state
}
