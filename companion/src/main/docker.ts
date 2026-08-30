import { exec } from 'child_process'
import { promisify } from 'util'

const defaultExec = promisify(exec)

export type ExecFunction = (cmd: string) => Promise<{ stdout: string; stderr: string }>

export interface ContainerStatus {
  dockerAvailable: boolean
  containerExists: boolean
  running: boolean
  ayugramRunning: boolean
  password?: string
  error?: string
}

export class DockerController {
  private containerName = 'ayugram-dev-ui'

  constructor(private execFn: ExecFunction = defaultExec) {}

  async checkStatus(): Promise<ContainerStatus> {
    try {
      await this.execFn('docker --version')
    } catch {
      return {
        dockerAvailable: false,
        containerExists: false,
        running: false,
        ayugramRunning: false,
        error: 'Docker CLI not found on host machine'
      }
    }

    try {
      const { stdout: containerList } = await this.execFn(
        `docker ps -a --filter "name=^/${this.containerName}$" --format "{{.Names}}"`
      )

      const exists = containerList.trim().includes(this.containerName)
      if (!exists) {
        return {
          dockerAvailable: true,
          containerExists: false,
          running: false,
          ayugramRunning: false,
          error: `Container ${this.containerName} does not exist.`
        }
      }

      const { stdout: runningCheck } = await this.execFn(
        `docker inspect --format "{{.State.Running}}" ${this.containerName}`
      )
      const running = runningCheck.trim() === 'true'

      if (!running) {
        return {
          dockerAvailable: true,
          containerExists: true,
          running: false,
          ayugramRunning: false
        }
      }

      let ayugramRunning = false
      let password = ''

      try {
        const { stdout: pgrepOut } = await this.execFn(
          `docker exec ${this.containerName} bash -lc "pgrep -x AyuGram || true"`
        )
        ayugramRunning = pgrepOut.trim().length > 0
      } catch {
        ayugramRunning = false
      }

      try {
        const { stdout: pwdOut } = await this.execFn(
          `docker exec ${this.containerName} cat /home/user/.local/state/ayugram-desktop/password`
        )
        password = pwdOut.trim()
      } catch {
        password = ''
      }

      return {
        dockerAvailable: true,
        containerExists: true,
        running: true,
        ayugramRunning,
        password
      }
    } catch (err: unknown) {
      return {
        dockerAvailable: true,
        containerExists: false,
        running: false,
        ayugramRunning: false,
        error: err instanceof Error ? err.message : String(err)
      }
    }
  }

  async startContainer(): Promise<{ success: boolean; message: string }> {
    try {
      await this.execFn(`docker start ${this.containerName}`)
      return { success: true, message: `Container ${this.containerName} started.` }
    } catch (err: unknown) {
      return {
        success: false,
        message: err instanceof Error ? err.message : String(err)
      }
    }
  }

  async restartAyuGram(): Promise<{ success: boolean; message: string }> {
    try {
      await this.execFn(
        `docker exec ${this.containerName} bash -lc "pkill -x AyuGram || true; sleep 1; DISPLAY=:1 /usr/local/bin/launch-ayugram >/tmp/ayugram-runtime.log 2>&1 &"`
      )
      return { success: true, message: 'AyuGram process restarted.' }
    } catch (err: unknown) {
      return {
        success: false,
        message: err instanceof Error ? err.message : String(err)
      }
    }
  }

  async getLogs(lines = 100): Promise<string> {
    try {
      const { stdout } = await this.execFn(
        `docker exec ${this.containerName} bash -lc "tail -n ${lines} /home/user/.local/state/ayugram-desktop/ayugram.log 2>/dev/null || tail -n ${lines} /tmp/ayugram-runtime.log 2>/dev/null || docker logs --tail ${lines} ${this.containerName} 2>&1"`
      )
      return stdout
    } catch (err: unknown) {
      return `Error fetching logs: ${err instanceof Error ? err.message : String(err)}`
    }
  }
}
