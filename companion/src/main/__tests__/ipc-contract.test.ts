import { describe, it, expect, vi } from 'vitest'
import { setupIpc } from '../ipc'
import { DockerController } from '../docker'
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

describe('IPC Contract Verification', () => {
  it('registers all required invoke and send channels required by the Preload API', () => {
    const docker = new DockerController()
    setupIpc(docker)

    // Expected channels defined in preload API
    const expectedInvokeChannels = [
      'docker:check-status',
      'docker:start-container',
      'docker:restart-ayugram',
      'docker:get-logs',
      'window:is-maximized'
    ]

    const expectedSendChannels = [
      'window:minimize',
      'window:maximize',
      'window:close'
    ]

    for (const channel of expectedInvokeChannels) {
      expect(ipcMain.handle).toHaveBeenCalledWith(channel, expect.any(Function))
    }

    for (const channel of expectedSendChannels) {
      expect(ipcMain.on).toHaveBeenCalledWith(channel, expect.any(Function))
    }
  })
})
