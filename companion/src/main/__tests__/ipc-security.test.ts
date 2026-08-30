import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setupIpc } from '../ipc'
import { DockerController, ExecFunction } from '../docker'
import { ipcMain } from 'electron'

vi.mock('electron', () => {
  const handlers = new Map<string, Function>()
  const listeners = new Map<string, Function>()

  return {
    ipcMain: {
      handle: vi.fn((channel: string, fn: Function) => {
        handlers.set(channel, fn)
      }),
      on: vi.fn((channel: string, fn: Function) => {
        listeners.set(channel, fn)
      }),
      _handlers: handlers,
      _listeners: listeners
    },
    BrowserWindow: {
      fromWebContents: vi.fn().mockReturnValue({
        minimize: vi.fn(),
        maximize: vi.fn(),
        unmaximize: vi.fn(),
        isMaximized: vi.fn().mockReturnValue(false),
        close: vi.fn()
      })
    }
  }
})

describe('IPC Security & Boundary Defense Tests', () => {
  let mockExec: ReturnType<typeof vi.fn<ExecFunction>>
  let docker: DockerController

  beforeEach(() => {
    vi.clearAllMocks()
    mockExec = vi.fn<ExecFunction>().mockResolvedValue({ stdout: 'log line', stderr: '' })
    docker = new DockerController(mockExec)
    setupIpc(docker)
  })

  it('bounds excessive log lines requested to safe maximum (500) preventing resource exhaustion', async () => {
    // @ts-expect-error accessing test harness
    const getLogsHandler = ipcMain._handlers.get('docker:get-logs')
    expect(getLogsHandler).toBeDefined()

    await getLogsHandler({}, 999999)
    expect(mockExec).toHaveBeenCalledWith(expect.stringContaining('tail -n 500'))
  })

  it('bounds negative or zero log lines to safe minimum (1)', async () => {
    // @ts-expect-error accessing test harness
    const getLogsHandler = ipcMain._handlers.get('docker:get-logs')

    await getLogsHandler({}, -50)
    expect(mockExec).toHaveBeenCalledWith(expect.stringContaining('tail -n 1'))

    await getLogsHandler({}, 0)
    expect(mockExec).toHaveBeenCalledWith(expect.stringContaining('tail -n 1'))
  })

  it('handles invalid injection types in logs parameter falling back to default 100', async () => {
    // @ts-expect-error accessing test harness
    const getLogsHandler = ipcMain._handlers.get('docker:get-logs')

    await getLogsHandler({}, '; rm -rf / ;')
    expect(mockExec).toHaveBeenCalledWith(expect.stringContaining('tail -n 100'))

    await getLogsHandler({}, { malicious: true })
    expect(mockExec).toHaveBeenCalledWith(expect.stringContaining('tail -n 100'))
  })
})
