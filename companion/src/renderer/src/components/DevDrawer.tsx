import React, { useState } from 'react'
import {
  X,
  RotateCcw,
  Play,
  Terminal,
  Info,
  ShieldCheck,
  Activity,
  Eye,
  EyeOff,
  Copy,
  Check,
  ShieldAlert,
  GitBranch,
  RefreshCw,
  Zap
} from 'lucide-react'

interface DevDrawerProps {
  isOpen: boolean
  onClose: () => void
  running: boolean
  ayugramRunning: boolean
  password?: string
  onStartContainer: () => void
  onRestartAyuGram: () => void
  onOpenLogs: () => void
  onRunScript: (commandId: string, title: string) => void
}

export const DevDrawer: React.FC<DevDrawerProps> = ({
  isOpen,
  onClose,
  running,
  ayugramRunning,
  password,
  onStartContainer,
  onRestartAyuGram,
  onOpenLogs,
  onRunScript
}) => {
  const [showToken, setShowToken] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (password) {
      navigator.clipboard.writeText(password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <aside className={`dev-drawer ${isOpen ? 'open' : ''}`}>
      <div className="drawer-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={18} color="#38bdf8" />
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>Dev Command Center</h3>
        </div>
        <button className="titlebar-btn" onClick={onClose} aria-label="Fechar painel">
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

        {/* In-App Command Runner Card */}
        <div className="card">
          <span className="card-title">Comandos & Automação 360°</span>

          <button
            className="action-btn primary"
            onClick={() => onRunScript('verify-release-360', 'Auditoria Canônica 16-Gate (G1-G16)')}
          >
            <ShieldCheck size={16} />
            <span>Executar Auditoria 16-Gate 360°</span>
          </button>

          <button
            className="action-btn secondary"
            onClick={() => onRunScript('chaos-recovery', 'Teste de Resiliência Chaos-Lite')}
          >
            <Zap size={16} color="#f59e0b" />
            <span>Executar Teste Chaos Recovery</span>
          </button>

          <button
            className="action-btn secondary"
            onClick={onRestartAyuGram}
            disabled={!running}
            style={{ opacity: running ? 1 : 0.5 }}
          >
            <RotateCcw size={15} />
            <span>Reiniciar Processo AyuGram</span>
          </button>

          {!running ? (
            <button className="action-btn primary" onClick={onStartContainer}>
              <Play size={15} fill="currentColor" />
              <span>Iniciar Container Docker</span>
            </button>
          ) : (
            <button
              className="action-btn secondary"
              onClick={() => onRunScript('restart-container', 'Reiniciar Container Docker')}
            >
              <RefreshCw size={15} />
              <span>Reiniciar Container Docker</span>
            </button>
          )}

          <button
            className="action-btn secondary"
            onClick={() => onRunScript('git-status', 'Status Git & Reconciliação')}
          >
            <GitBranch size={15} />
            <span>Verificar Status Git & Reconciliação</span>
          </button>

          <button className="action-btn secondary" onClick={onOpenLogs}>
            <Terminal size={15} />
            <span>Inspecionar Logs do Runtime</span>
          </button>
        </div>

        {/* Security & Token Card */}
        <div className="card">
          <span className="card-title">Credenciais & Acesso</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
            <ShieldAlert size={14} color="#34d399" />
            <span>Autenticação Local Automática</span>
          </div>
          {password && (
            <div style={{ marginTop: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: '#64748b' }}>Token de Sessão:</span>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    className="titlebar-btn"
                    style={{ width: 22, height: 22 }}
                    onClick={() => setShowToken((prev) => !prev)}
                    title={showToken ? 'Ocultar' : 'Mostrar'}
                  >
                    {showToken ? <EyeOff size={12} /> : <Eye size={12} />}
                  </button>
                  <button
                    className="titlebar-btn"
                    style={{ width: 22, height: 22 }}
                    onClick={handleCopy}
                    title="Copiar token"
                  >
                    {copied ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                  </button>
                </div>
              </div>
              <input
                type={showToken ? 'text' : 'password'}
                readOnly
                value={password}
                aria-label="VNC Session Token"
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
              Execução direta de gates, diagnóstico e comandos com stream de saída em tempo real no app.
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}
