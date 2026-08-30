import { useState, useEffect, useCallback } from 'react'

export interface DockerState {
  dockerAvailable: boolean
  containerExists: boolean
  running: boolean
  ayugramRunning: boolean
  password?: string
  error?: string
  loading: boolean
}

export function useDocker() {
  const [state, setState] = useState<DockerState>({
    dockerAvailable: true,
    containerExists: true,
    running: false,
    ayugramRunning: false,
    loading: true
  })

  const refreshStatus = useCallback(async () => {
    try {
      if (!window.ayugramApi) {
        setState((prev) => ({ ...prev, loading: false, error: 'ayugramApi not available' }))
        return
      }
      const res = await window.ayugramApi.docker.checkStatus()
      setState({
        ...res,
        loading: false
      })
    } catch (err: unknown) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : String(err)
      }))
    }
  }, [])

  const startContainer = async () => {
    setState((prev) => ({ ...prev, loading: true }))
    try {
      const res = await window.ayugramApi.docker.startContainer()
      await refreshStatus()
      return res
    } catch (err: unknown) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : String(err)
      }))
      return { success: false, message: String(err) }
    }
  }

  const restartAyuGram = async () => {
    try {
      const res = await window.ayugramApi.docker.restartAyuGram()
      await refreshStatus()
      return res
    } catch (err: unknown) {
      return { success: false, message: String(err) }
    }
  }

  const fetchLogs = async (lines = 100) => {
    try {
      return await window.ayugramApi.docker.getLogs(lines)
    } catch (err: unknown) {
      return `Failed to fetch logs: ${String(err)}`
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 4000)
    return () => clearInterval(interval)
  }, [refreshStatus])

  return {
    ...state,
    refreshStatus,
    startContainer,
    restartAyuGram,
    fetchLogs
  }
}
