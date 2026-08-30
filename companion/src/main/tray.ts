import { Tray, Menu, nativeImage, BrowserWindow, app } from 'electron'
import { DockerController } from './docker'

let tray: Tray | null = null

export function setupTray(mainWindow: BrowserWindow, docker: DockerController): Tray {
  // Create simple 16x16 icon programmatically if asset icon not provided
  const icon = nativeImage.createFromBuffer(
    Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAA7SURBVDhPY/wPBAwUACYoTawBDEQZQJQB6BqIMgBFA1EGoGogzACiDSBaBqBoIMwAog0gWgagaCDKAAA7pA0Vz6zV7QAAAABJRU5ErkJggg==',
      'base64'
    )
  )

  tray = new Tray(icon)
  tray.setToolTip('AyuGram Native Shell')

  const updateMenu = async () => {
    const status = await docker.checkStatus()
    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'AyuGram Native Shell',
        enabled: false
      },
      { type: 'separator' },
      {
        label: status.running ? '🟢 Docker Running' : '🔴 Docker Stopped',
        enabled: false
      },
      {
        label: status.ayugramRunning ? '🟢 AyuGram Active' : '⚪ AyuGram Inactive',
        enabled: false
      },
      { type: 'separator' },
      {
        label: 'Abrir Janela',
        click: () => {
          mainWindow.show()
          mainWindow.focus()
        }
      },
      {
        label: 'Reiniciar AyuGram',
        enabled: status.running,
        click: async () => {
          await docker.restartAyuGram()
        }
      },
      { type: 'separator' },
      {
        label: 'Sair',
        click: () => {
          app.quit()
        }
      }
    ])
    tray?.setContextMenu(contextMenu)
  }

  tray.on('double-click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })

  updateMenu()
  setInterval(updateMenu, 10000)

  return tray
}
