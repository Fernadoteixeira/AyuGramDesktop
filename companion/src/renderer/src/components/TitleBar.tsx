import React from 'react'
import { StatusBadge } from './StatusBadge'
import { Minus, Square, X, Terminal, Cpu } from 'lucide-react'

interface TitleBarProps {
  running: boolean
  ayugramRunning: boolean
  loading: boolean
  onToggleDrawer: () => void
  onOpenLogs: () => void
}

export const TitleBar: React.FC<TitleBarProps> = ({
  running,
  ayugramRunning,
  loading,
  onToggleDrawer,
  onOpenLogs
}) => {
  const handleMinimize = () => window.ayugramApi?.window.minimize()
  const handleMaximize = () => window.ayugramApi?.window.maximize()
  const handleClose = () => window.ayugramApi?.window.close()

  return (
    <header className="titlebar">
      <div className="titlebar-brand">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" fill="url(#grad)" />
          <path d="M7 12L10.5 15.5L17 9" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
          <defs>
            <linearGradient id="grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
              <stop stopColor="#06b6d4" />
              <stop offset="1" stopColor="#3b82f6" />
            </linearGradient>
          </defs>
        </svg>
        <span>AYUGRAM NATIVE SHELL</span>
      </div>

      <div className="titlebar-center">
        <StatusBadge running={running} ayugramRunning={ayugramRunning} loading={loading} />
      </div>

      <div className="titlebar-actions">
        <button
          className="titlebar-btn"
          title="Ver Logs"
          onClick={onOpenLogs}
        >
          <Terminal size={14} />
        </button>

        <button
          className="titlebar-btn"
          title="Dev Control Center"
          onClick={onToggleDrawer}
        >
          <Cpu size={14} />
        </button>

        <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.1)', margin: '0 4px' }} />

        <button className="titlebar-btn" title="Minimizar" onClick={handleMinimize}>
          <Minus size={14} />
        </button>
        <button className="titlebar-btn" title="Maximizar / Restaurar" onClick={handleMaximize}>
          <Square size={12} />
        </button>
        <button className="titlebar-btn btn-close" title="Fechar" onClick={handleClose}>
          <X size={14} />
        </button>
      </div>
    </header>
  )
}
