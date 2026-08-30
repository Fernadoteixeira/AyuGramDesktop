import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TitleBar } from '../components/TitleBar'

describe('TitleBar', () => {
  it('renders brand title and triggers actions', () => {
    const onToggleDrawer = vi.fn()
    const onOpenLogs = vi.fn()

    render(
      <TitleBar
        running={true}
        ayugramRunning={true}
        loading={false}
        onToggleDrawer={onToggleDrawer}
        onOpenLogs={onOpenLogs}
      />
    )

    expect(screen.getByText('AYUGRAM NATIVE SHELL')).toBeInTheDocument()

    const logsBtn = screen.getByTitle('Ver Logs')
    fireEvent.click(logsBtn)
    expect(onOpenLogs).toHaveBeenCalledTimes(1)

    const drawerBtn = screen.getByTitle('Dev Control Center')
    fireEvent.click(drawerBtn)
    expect(onToggleDrawer).toHaveBeenCalledTimes(1)
  })

  it('triggers window minimization, maximization, and close', () => {
    render(
      <TitleBar
        running={true}
        ayugramRunning={true}
        loading={false}
        onToggleDrawer={vi.fn()}
        onOpenLogs={vi.fn()}
      />
    )

    const minBtn = screen.getByTitle('Minimizar')
    fireEvent.click(minBtn)
    expect(window.ayugramApi.window.minimize).toHaveBeenCalledTimes(1)

    const maxBtn = screen.getByTitle('Maximizar / Restaurar')
    fireEvent.click(maxBtn)
    expect(window.ayugramApi.window.maximize).toHaveBeenCalledTimes(1)

    const closeBtn = screen.getByTitle('Fechar')
    fireEvent.click(closeBtn)
    expect(window.ayugramApi.window.close).toHaveBeenCalledTimes(1)
  })
})
