import React from 'react'
import { X, RotateCcw, Play, Terminal, Info, ShieldCheck, Activity } from 'lucide-react'

interface DevDrawerProps {
  isOpen: boolean
  onClose: () => void
  running: boolean
  ayugramRunning: boolean
  password?: string
  onStartContainer: () => void
  onRestartAyuGram: () => void
  onOpenLogs: () => void
}

export const DevDrawer: React.FC<DevDrawerProps> = ({
  isOpen,
  onClose,
  running,
  ayugramRunning,
  password,
  onStartContainer,
  onRestartAyuGram,
  onOpenLogs
}) => {
  return (
    <aside className={`dev-drawer ${isOpen ? 'open' : ''}`}>
      <div className="drawer-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={18} color="#38bdf8" />
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Dev Control Center</h3>
        </div>
        <button className="titlebar-btn" onClick={onClose}>
          <X size={16} />
        </button>
      </div>

      <div className="drawer-body">
        {/* Environment Status Card */}
        <div className="card">
          <span className="card-title">Ambiente de Desenvolvimento</span>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <span style={{ color: '#94a3b8' }}>Docker Container:</span>
            <span style={{ fontWeight: 600, color: running ? '#34d399' : '#f87171' }}>
              {running ? 'ayugram-dev-ui (Running)' : 'Parado'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <span style={{ color: '#94a3b8' }}>Processo C++ AyuGram:</span>
            <span style={{ fontWeight: 600, color: ayugramRunning ? '#34d399' : '#fbbf24' }}>
              {ayugramRunning ? 'Ativo (X11 :1)' : 'Inativo'}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
            <span style={{ color: '#94a3b8' }}>Display & Resolução:</span>
            <span style={{ fontWeight: 500, color: '#e2e8f0' }}>1920x1080 (Xvfb)</span>
          </div>
        </div>

        {/* Quick Actions Card */}
        <div className="card">
          <span className="card-title">Ações Rápidas</span>
          <button
            className="action-btn primary"
            onClick={onRestartAyuGram}
            disabled={!running}
            style={{ opacity: running ? 1 : 0.5 }}
          >
            <RotateCcw size={15} />
            <span>Reiniciar Processo AyuGram</span>
          </button>

          {!running && (
            <button className="action-btn secondary" onClick={onStartContainer}>
              <Play size={15} fill="currentColor" />
              <span>Iniciar Container Docker</span>
            </button>
          )}

          <button className="action-btn secondary" onClick={onOpenLogs}>
            <Terminal size={15} />
            <span>Inspecionar Logs do Runtime</span>
          </button>
        </div>

        {/* Security & Token Card */}
        <div className="card">
          <span className="card-title">Credenciais & Acesso</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
            <ShieldCheck size={14} color="#34d399" />
            <span>Autenticação VNC Automática</span>
          </div>
          {password && (
            <div style={{ marginTop: 4 }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>Token VNC:</div>
              <input
                readOnly
                value={password}
                style={{
                  width: '100%',
                  background: '#05070e',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 6,
                  padding: '6px 10px',
                  color: '#94a3b8',
                  fontSize: 11,
                  fontFamily: 'monospace'
                }}
              />
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="card" style={{ background: 'rgba(15, 23, 42, 0.4)' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <Info size={16} color="#38bdf8" style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
              O AyuGram Native Shell conecta diretamente ao servidor X11/noVNC interno da imagem Rocky Linux via socket seguro local.
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}
