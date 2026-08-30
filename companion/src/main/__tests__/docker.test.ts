import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DockerController, ExecFunction } from '../docker'

describe('DockerController (Main Process)', () => {
  let mockExec: ReturnType<typeof vi.fn<ExecFunction>>
  let controller: DockerController

  beforeEach(() => {
    mockExec = vi.fn<ExecFunction>()
    controller = new DockerController(mockExec)
  })

  it('handles Docker CLI not being installed gracefully', async () => {
    mockExec.mockRejectedValue(new Error('command not found: docker'))

    const status = await controller.checkStatus()
    expect(status.dockerAvailable).toBe(false)
    expect(status.running).toBe(false)
    expect(status.error).toContain('Docker CLI not found')
  })

  it('handles non-existent container', async () => {
    mockExec.mockImplementation(async (cmd: string) => {
      if (cmd.includes('docker --version')) {
        return { stdout: 'Docker version 24.0.0', stderr: '' }
      }
      if (cmd.includes('docker ps -a')) {
        return { stdout: 'other-container\n', stderr: '' }
      }
      return { stdout: '', stderr: '' }
    })

    const status = await controller.checkStatus()
    expect(status.dockerAvailable).toBe(true)
    expect(status.containerExists).toBe(false)
    expect(status.running).toBe(false)
  })

  it('detects running container with active AyuGram process and parses password', async () => {
    mockExec.mockImplementation(async (cmd: string) => {
      if (cmd.includes('docker --version')) {
        return { stdout: 'Docker version 24.0.0', stderr: '' }
      }
      if (cmd.includes('docker ps -a')) {
        return { stdout: 'ayugram-dev-ui\n', stderr: '' }
      }
      if (cmd.includes('docker inspect')) {
        return { stdout: 'true\n', stderr: '' }
      }
      if (cmd.includes('pgrep -x AyuGram')) {
        return { stdout: '12345\n', stderr: '' }
      }
      if (cmd.includes('cat /home/user/.local/state/ayugram-desktop/password')) {
        return { stdout: 'vnc_secret_token_123\n', stderr: '' }
      }
      return { stdout: '', stderr: '' }
    })

    const status = await controller.checkStatus()
    expect(status.dockerAvailable).toBe(true)
    expect(status.containerExists).toBe(true)
    expect(status.running).toBe(true)
    expect(status.ayugramRunning).toBe(true)
    expect(status.password).toBe('vnc_secret_token_123')
  })

  it('triggers container start command correctly', async () => {
    mockExec.mockResolvedValue({ stdout: 'ayugram-dev-ui', stderr: '' })

    const res = await controller.startContainer()
    expect(res.success).toBe(true)
    expect(mockExec).toHaveBeenCalledWith('docker start ayugram-dev-ui')
  })

  it('triggers restart AyuGram command with correct X11 display environment', async () => {
    mockExec.mockResolvedValue({ stdout: 'ok', stderr: '' })

    const res = await controller.restartAyuGram()
    expect(res.success).toBe(true)
    expect(mockExec).toHaveBeenCalledWith(
      expect.stringContaining('DISPLAY=:1')
    )
    expect(mockExec).toHaveBeenCalledWith(
      expect.stringContaining('launch-ayugram')
    )
  })
})
