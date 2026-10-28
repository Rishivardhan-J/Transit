import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useLiveChannel } from '../hooks/useLiveChannel'

class FakeSocket {
  static instances: FakeSocket[] = []
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  url: string
  constructor(url: string) { this.url = url; FakeSocket.instances.push(this) }
  close() { this.onclose?.() }
}

beforeEach(() => { vi.useFakeTimers(); FakeSocket.instances = []; vi.stubGlobal('WebSocket', FakeSocket) })
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

describe('useLiveChannel', () => {
  it('delivers messages and reports live once connected', () => {
    const onMessage = vi.fn()
    const { result } = renderHook(() => useLiveChannel({ url: 'ws://x/jobs/1', onMessage }))
    act(() => FakeSocket.instances[0].onopen?.())
    expect(result.current).toBe('live')
    act(() => FakeSocket.instances[0].onmessage?.({ data: JSON.stringify({ status: 'running' }) }))
    expect(onMessage).toHaveBeenCalledWith({ status: 'running' })
  })

  it('falls back to polling when the socket drops, then reconnects with backoff', () => {
    const poll = vi.fn()
    const { result } = renderHook(() => useLiveChannel({ url: 'ws://x/jobs/1', onMessage: vi.fn(), poll, pollMs: 1000 }))
    act(() => FakeSocket.instances[0].onopen?.())
    act(() => FakeSocket.instances[0].onclose?.())
    expect(result.current).toBe('polling')
    act(() => { vi.advanceTimersByTime(2500) })
    expect(poll).toHaveBeenCalled()
    expect(FakeSocket.instances.length).toBeGreaterThan(1)                       // reconnect attempted
    act(() => FakeSocket.instances.at(-1)!.onopen?.())
    expect(result.current).toBe('live')
  })

  it('stays off without a url and stops after a final message', () => {
    const { result: off } = renderHook(() => useLiveChannel({ url: null, onMessage: vi.fn() }))
    expect(off.current).toBe('off')
    const { result } = renderHook(() => useLiveChannel<{ status: string }>({ url: 'ws://x', onMessage: vi.fn(), isFinal: (m) => m.status === 'completed' }))
    act(() => FakeSocket.instances.at(-1)!.onopen?.())
    act(() => FakeSocket.instances.at(-1)!.onmessage?.({ data: JSON.stringify({ status: 'completed' }) }))
    expect(result.current).toBe('off')
  })
})
