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
    fetchLogs
  } = useDocker()

  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false)

  return (
    <div className="app-container">
      <TitleBar
        running={running}
        ayugramRunning={ayugramRunning}
        loading={loading}
        onToggleDrawer={() => setIsDrawerOpen((prev) => !prev)}
        onOpenLogs={() => setIsLogViewerOpen(true)}
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
        onOpenLogs={() => setIsLogViewerOpen(true)}
      />

      <LogViewer
        isOpen={isLogViewerOpen}
        onClose={() => setIsLogViewerOpen(false)}
        fetchLogs={fetchLogs}
      />
    </div>
  )
}
