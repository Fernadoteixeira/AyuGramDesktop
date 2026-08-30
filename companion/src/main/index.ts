import { app, BrowserWindow, shell, session } from 'electron'
import { join } from 'path'
import { DockerController } from './docker'
import { setupIpc } from './ipc'
import { setupTray } from './tray'

let mainWindow: BrowserWindow | null = null
const docker = new DockerController()

function setupSecurityPolicies(): void {
  // Enforce runtime Content-Security-Policy (CSP) headers
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:6080 ws://127.0.0.1:6080 http://localhost:6080 ws://localhost:6080 data: blob:;"
        ]
      }
    })
  })
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    show: false,
    frame: false,
    backgroundColor: '#0a0e17',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      webviewTag: true,
      webSecurity: true,
      allowRunningInsecureContent: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show()
  })

  // Navigation Guard: Prevent arbitrary navigation inside the Electron main window
  mainWindow.webContents.on('will-navigate', (event, url) => {
    const isDevUrl = process.env['ELECTRON_RENDERER_URL'] && url.startsWith(process.env['ELECTRON_RENDERER_URL'])
    const isLocalFile = url.startsWith('file://')
    if (!isDevUrl && !isLocalFile) {
      event.preventDefault()
    }
  })

  // Secure External Link Handling: Only allow external opening of verified https:// schemes
  mainWindow.webContents.setWindowOpenHandler((details) => {
    try {
      const parsedUrl = new URL(details.url)
      if (parsedUrl.protocol === 'https:') {
        shell.openExternal(details.url)
      }
    } catch {
      // Ignore invalid URLs
    }
    return { action: 'deny' }
  })

  setupIpc(docker)
  setupTray(mainWindow, docker)

  // Load renderer
  if (process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  setupSecurityPolicies()
  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
