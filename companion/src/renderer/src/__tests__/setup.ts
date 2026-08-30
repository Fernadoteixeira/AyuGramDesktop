import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock Electron window.ayugramApi
Object.defineProperty(window, 'ayugramApi', {
  value: {
    docker: {
      checkStatus: vi.fn().mockResolvedValue({
        dockerAvailable: true,
        containerExists: true,
        running: true,
        ayugramRunning: true,
        password: 'test-password'
      }),
      startContainer: vi.fn().mockResolvedValue({ success: true, message: 'Container started' }),
      restartAyuGram: vi.fn().mockResolvedValue({ success: true, message: 'AyuGram restarted' }),
      getLogs: vi.fn().mockResolvedValue('Sample log output line 1\nSample log output line 2'),
      executeScript: vi.fn().mockResolvedValue({ success: true, output: 'Command output test' })
    },
    window: {
      minimize: vi.fn(),
      maximize: vi.fn(),
      close: vi.fn(),
      isMaximized: vi.fn().mockResolvedValue(false)
    }
  },
  writable: true
})
