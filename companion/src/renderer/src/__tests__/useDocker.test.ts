import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDocker } from '../hooks/useDocker'

describe('useDocker Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes and polls docker status from ayugramApi', async () => {
    const { result } = renderHook(() => useDocker())

    expect(result.current.loading).toBe(true)

    await act(async () => {
      await result.current.refreshStatus()
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.running).toBe(true)
    expect(result.current.ayugramRunning).toBe(true)
    expect(result.current.password).toBe('test-password')
    expect(window.ayugramApi.docker.checkStatus).toHaveBeenCalled()
  })

  it('triggers restartAyuGram via API', async () => {
    const { result } = renderHook(() => useDocker())

    await act(async () => {
      const res = await result.current.restartAyuGram()
      expect(res.success).toBe(true)
    })

    expect(window.ayugramApi.docker.restartAyuGram).toHaveBeenCalledTimes(1)
  })

  it('triggers startContainer via API', async () => {
    const { result } = renderHook(() => useDocker())

    await act(async () => {
      const res = await result.current.startContainer()
      expect(res.success).toBe(true)
    })

    expect(window.ayugramApi.docker.startContainer).toHaveBeenCalledTimes(1)
  })

  it('fetches logs via API', async () => {
    const { result } = renderHook(() => useDocker())

    let logs = ''
    await act(async () => {
      logs = await result.current.fetchLogs(50)
    })

    expect(logs).toContain('Sample log output')
    expect(window.ayugramApi.docker.getLogs).toHaveBeenCalledWith(50)
  })
})
