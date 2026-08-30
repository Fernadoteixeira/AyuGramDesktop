import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DevDrawer } from '../components/DevDrawer'

describe('DevDrawer', () => {
  it('renders correctly when open and triggers restart, script execution, and logs', () => {
    const onClose = vi.fn()
    const onStartContainer = vi.fn()
    const onRestartAyuGram = vi.fn()
    const onOpenLogs = vi.fn()
    const onRunScript = vi.fn()

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
        onRunScript={onRunScript}
      />
    )

    expect(screen.getByText('Dev Command Center')).toBeInTheDocument()
    
    // Masked by default as password type
    const tokenInput = screen.getByLabelText('VNC Session Token') as HTMLInputElement
    expect(tokenInput.type).toBe('password')
    expect(tokenInput.value).toBe('secret-password')

    // Toggle reveal
    const toggleBtn = screen.getByTitle('Mostrar')
    fireEvent.click(toggleBtn)
    expect(tokenInput.type).toBe('text')

    const auditBtn = screen.getByText('Executar Auditoria 16-Gate 360°')
    fireEvent.click(auditBtn)
    expect(onRunScript).toHaveBeenCalledWith('verify-release-360', 'Auditoria Canônica 16-Gate (G1-G16)')

    const chaosBtn = screen.getByText('Executar Teste Chaos Recovery')
    fireEvent.click(chaosBtn)
    expect(onRunScript).toHaveBeenCalledWith('chaos-recovery', 'Teste de Resiliência Chaos-Lite')

    const restartBtn = screen.getByText('Reiniciar Processo AyuGram')
    fireEvent.click(restartBtn)
    expect(onRestartAyuGram).toHaveBeenCalledTimes(1)

    const logsBtn = screen.getByText('Inspecionar Logs do Runtime')
    fireEvent.click(logsBtn)
    expect(onOpenLogs).toHaveBeenCalledTimes(1)
  })
})
