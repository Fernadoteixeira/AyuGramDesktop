import { contextBridge, ipcRenderer } from 'electron'

export interface AyuGramApi {
  docker: {
    checkStatus: () => Promise<{
      dockerAvailable: boolean
      containerExists: boolean
      running: boolean
      ayugramRunning: boolean
      password?: string
      error?: string
    }>
    startContainer: () => Promise<{ success: boolean; message: string }>
    restartAyuGram: () => Promise<{ success: boolean; message: string }>
    getLogs: (lines?: number) => Promise<string>
  }
  window: {
    minimize: () => void
    maximize: () => void
    close: () => void
    isMaximized: () => Promise<boolean>
  }
}

const api: AyuGramApi = {
  docker: {
    checkStatus: () => ipcRenderer.invoke('docker:check-status'),
    startContainer: () => ipcRenderer.invoke('docker:start-container'),
    restartAyuGram: () => ipcRenderer.invoke('docker:restart-ayugram'),
    getLogs: (lines?: number) => ipcRenderer.invoke('docker:get-logs', lines)
  },
  window: {
    minimize: () => ipcRenderer.send('window:minimize'),
    maximize: () => ipcRenderer.send('window:maximize'),
    close: () => ipcRenderer.send('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:is-maximized')
  }
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('ayugramApi', api)
  } catch (error) {
    console.error('Error exposing contextBridge API:', error)
  }
} else {
  // @ts-ignore (define in window)
  window.ayugramApi = api
}
