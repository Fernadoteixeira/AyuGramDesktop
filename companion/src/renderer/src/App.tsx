import React, { useState } from 'react'
import { useDocker } from './hooks/useDocker'
import { TitleBar } from './components/TitleBar'
import { DisplayView } from './components/DisplayView'
import { DevDrawer } from './components/DevDrawer'
import { LogViewer } from './components/LogViewer'

export const App: React.FC = () => {
  const {
    running,
    ayugramRunning,
    password,
    loading,
    error,
    startContainer,
    restartAyuGram,
    fetchLogs,
    runScript
  } = useDocker()

  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false)
  const [scriptTitle, setScriptTitle] = useState<string | undefined>()
  const [scriptOutput, setScriptOutput] = useState<string | undefined>()
  const [isRunningScript, setIsRunningScript] = useState(false)
  const [activeCommandId, setActiveCommandId] = useState<string | undefined>()

  const handleRunScript = async (commandId: string, title: string) => {
    setActiveCommandId(commandId)
    setScriptTitle(title)
    setScriptOutput('Iniciando execução do comando...\nAguarde o retorno da execução...\n')
    setIsRunningScript(true)
    setIsLogViewerOpen(true)

    try {
      const res = await runScript(commandId)
      setScriptOutput(res.output)
    } catch (err: unknown) {
      setScriptOutput(`Erro na execução:\n${String(err)}`)
    } finally {
      setIsRunningScript(false)
    }
  }

  const handleOpenStandardLogs = () => {
    setScriptTitle(undefined)
    setScriptOutput(undefined)
    setActiveCommandId(undefined)
    setIsLogViewerOpen(true)
  }

  return (
    <div className="app-container">
      <TitleBar
        running={running}
        ayugramRunning={ayugramRunning}
        loading={loading}
        onToggleDrawer={() => setIsDrawerOpen((prev) => !prev)}
        onOpenLogs={handleOpenStandardLogs}
      />

      <DisplayView
        running={running}
        ayugramRunning={ayugramRunning}
        password={password}
        loading={loading}
        error={error}
        onStartContainer={startContainer}
        onRestartAyuGram={restartAyuGram}
      />

      <DevDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        running={running}
        ayugramRunning={ayugramRunning}
        password={password}
        onStartContainer={startContainer}
        onRestartAyuGram={restartAyuGram}
        onOpenLogs={handleOpenStandardLogs}
        onRunScript={handleRunScript}
      />

      <LogViewer
        isOpen={isLogViewerOpen}
        onClose={() => setIsLogViewerOpen(false)}
        fetchLogs={fetchLogs}
        customTitle={scriptTitle}
        customContent={scriptOutput}
        isRunningScript={isRunningScript}
        onRerun={activeCommandId ? () => handleRunScript(activeCommandId, scriptTitle || 'Comando') : undefined}
      />
    </div>
  )
}
