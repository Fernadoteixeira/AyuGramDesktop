import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DevDrawer } from '../components/DevDrawer'

describe('DevDrawer', () => {
  it('renders correctly when open and triggers restart and logs', () => {
    const onClose = vi.fn()
    const onStartContainer = vi.fn()
    const onRestartAyuGram = vi.fn()
    const onOpenLogs = vi.fn()

    render(
      <DevDrawer
        isOpen={true}
        onClose={onClose}
        running={true}
        ayugramRunning={true}
        password="secret-password"
        onStartContainer={onStartContainer}
        onRestartAyuGram={onRestartAyuGram}
        onOpenLogs={onOpenLogs}
      />
    )

    expect(screen.getByText('Dev Control Center')).toBeInTheDocument()
    
    // Masked by default as password type
    const tokenInput = screen.getByLabelText('VNC Session Token') as HTMLInputElement
    expect(tokenInput.type).toBe('password')
    expect(tokenInput.value).toBe('secret-password')

    // Toggle reveal
    const toggleBtn = screen.getByTitle('Mostrar')
    fireEvent.click(toggleBtn)
    expect(tokenInput.type).toBe('text')

    const restartBtn = screen.getByText('Reiniciar Processo AyuGram')
    fireEvent.click(restartBtn)
    expect(onRestartAyuGram).toHaveBeenCalledTimes(1)

    const logsBtn = screen.getByText('Inspecionar Logs do Runtime')
    fireEvent.click(logsBtn)
    expect(onOpenLogs).toHaveBeenCalledTimes(1)
  })
})
