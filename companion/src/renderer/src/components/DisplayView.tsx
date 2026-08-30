import React, { useState } from 'react'
import { Play, RefreshCw, AlertTriangle, Monitor } from 'lucide-react'

interface DisplayViewProps {
  running: boolean
  ayugramRunning: boolean
  password?: string
  loading: boolean
  error?: string
  onStartContainer: () => void
  onRestartAyuGram: () => void
}

export const DisplayView: React.FC<DisplayViewProps> = ({
  running,
  ayugramRunning,
  password,
  loading,
  error,
  onStartContainer,
  onRestartAyuGram
}) => {
  const [iframeKey, setIframeKey] = useState(0)

  const handleRefresh = () => {
    setIframeKey((prev) => prev + 1)
  }

  if (loading) {
    return (
      <div className="main-content" style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
        <RefreshCw className="animate-spin" size={36} color="#38bdf8" />
        <p style={{ color: '#94a3b8', fontSize: 14 }}>Conectando ao ambiente AyuGram Desktop...</p>
      </div>
    )
  }

  if (!running) {
    return (
      <div className="main-content" style={{ alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20 }}>
        <div style={{
          width: 64,
          height: 64,
          borderRadius: 20,
          background: 'rgba(239, 68, 68, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(239, 68, 68, 0.2)'
        }}>
          <AlertTriangle size={32} color="#ef4444" />
        </div>

        <div style={{ textAlign: 'center', maxWidth: 460 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: '#f8fafc' }}>
            Container Docker Offline
          </h2>
          <p style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.6 }}>
            O container <code>ayugram-dev-ui</code> não está em execução no momento. Inicie-o para carregar o display nativo do AyuGram.
          </p>
          {error && (
            <p style={{ marginTop: 12, fontSize: 12, color: '#f87171', background: 'rgba(239,68,68,0.1)', padding: '8px 12px', borderRadius: 6 }}>
              {error}
            </p>
          )}
        </div>

        <button className="action-btn primary" onClick={onStartContainer} style={{ minWidth: 200 }}>
          <Play size={16} fill="white" />
          <span>Iniciar Container</span>
        </button>
      </div>
    )
  }

  const vncUrl = `http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale${password ? `&password=${encodeURIComponent(password)}` : ''}`

  return (
    <div className="main-content">
      <iframe
        key={iframeKey}
        src={vncUrl}
        className="viewport-iframe"
        title="AyuGram Desktop Viewport"
        allow="clipboard-read; clipboard-write; fullscreen"
      />

      <div className="floating-hud">
        {!ayugramRunning && (
          <button className="hud-btn" style={{ borderColor: '#f59e0b', color: '#fbbf24' }} onClick={onRestartAyuGram}>
            <Monitor size={14} />
            <span>Lançar AyuGram</span>
          </button>
        )}

        <button className="hud-btn" onClick={handleRefresh} title="Recarregar Visualizador">
          <RefreshCw size={14} />
          <span>Recarregar Stream</span>
        </button>
      </div>
    </div>
  )
}
