import { exec } from 'child_process'
import { promisify } from 'util'
import { join } from 'path'

const defaultExec = promisify(exec)

export type ExecFunction = (cmd: string, options?: { cwd?: string }) => Promise<{ stdout: string; stderr: string }>

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
  private repoRoot: string

  constructor(private execFn: ExecFunction = defaultExec) {
    this.repoRoot = join(__dirname, '../../..')
  }

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

  async executeScript(commandId: string): Promise<{ success: boolean; output: string }> {
    const ALLOWED_SCRIPTS: Record<string, string> = {
      'verify-release-360': 'python scripts/verify_companion_release_360.py',
      'verify-360': 'python scripts/verify_companion_360.py',
      'chaos-recovery': 'python scripts/test_chaos_recovery.py',
      'restart-ayugram': `docker exec ${this.containerName} bash -lc "pkill -x AyuGram || true; sleep 1; DISPLAY=:1 /usr/local/bin/launch-ayugram >/tmp/ayugram-runtime.log 2>&1 &"`,
      'restart-container': `docker restart ${this.containerName}`,
      'git-status': 'git status --short'
    }

    const cmd = ALLOWED_SCRIPTS[commandId]
    if (!cmd) {
      return { success: false, output: `Comando não autorizado ou desconhecido: ${commandId}` }
    }

    try {
      const { stdout, stderr } = await this.execFn(cmd, { cwd: this.repoRoot })
      return {
        success: true,
        output: (stdout + '\n' + stderr).trim() || 'Comando executado com sucesso.'
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      return {
        success: false,
        output: `Erro ao executar comando:\n${errorMsg}`
      }
    }
  }
}
