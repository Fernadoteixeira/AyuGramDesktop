import { ipcMain, BrowserWindow } from 'electron'
import { DockerController } from './docker'

export function setupIpc(docker: DockerController): void {
  ipcMain.handle('docker:check-status', async () => {
    return await docker.checkStatus()
  })

  ipcMain.handle('docker:start-container', async () => {
    return await docker.startContainer()
  })

  ipcMain.handle('docker:restart-ayugram', async () => {
    return await docker.restartAyuGram()
  })

  ipcMain.handle('docker:get-logs', async (_event, lines?: unknown) => {
    let safeLines = 100
    if (typeof lines === 'number' && Number.isInteger(lines)) {
      safeLines = Math.max(1, Math.min(lines, 500))
    }
    return await docker.getLogs(safeLines)
  })

  ipcMain.handle('companion:execute-script', async (_event, commandId: unknown) => {
    if (typeof commandId !== 'string') {
      return { success: false, output: 'ID de comando inválido.' }
    }
    return await docker.executeScript(commandId)
  })

  ipcMain.on('window:minimize', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    win?.minimize()
  })

  ipcMain.on('window:maximize', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    if (win) {
      if (win.isMaximized()) {
        win.unmaximize()
      } else {
        win.maximize()
      }
    }
  })

  ipcMain.on('window:close', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    win?.close()
  })

  ipcMain.handle('window:is-maximized', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    return win?.isMaximized() ?? false
  })
}
