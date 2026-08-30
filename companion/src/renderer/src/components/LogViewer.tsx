import React, { useState, useEffect } from 'react'
import { X, RefreshCw, Copy, Check, Terminal, Play } from 'lucide-react'

interface LogViewerProps {
  isOpen: boolean
  onClose: () => void
  fetchLogs: (lines?: number) => Promise<string>
  customTitle?: string
  customContent?: string
  isRunningScript?: boolean
  onRerun?: () => void
}

export const LogViewer: React.FC<LogViewerProps> = ({
  isOpen,
  onClose,
  fetchLogs,
  customTitle,
  customContent,
  isRunningScript,
  onRerun
}) => {
  const [logs, setLogs] = useState<string>('Carregando...')
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const loadLogs = async () => {
    if (customContent !== undefined) {
      setLogs(customContent)
      return
    }
    setLoading(true)
    const res = await fetchLogs(150)
    setLogs(res || 'Nenhum log encontrado.')
    setLoading(false)
  }

  useEffect(() => {
    if (isOpen) {
      if (customContent !== undefined) {
        setLogs(customContent)
      } else {
        loadLogs()
      }
    }
  }, [isOpen, customContent])

  const handleCopy = () => {
    navigator.clipboard.writeText(logs)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 850 }}>
        <div className="drawer-header" style={{ padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={16} color="#38bdf8" />
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
              {customTitle || 'Logs de Runtime (AyuGram / Docker)'}
            </h3>
            {isRunningScript && (
              <span style={{ fontSize: 11, background: '#0284c7', color: '#fff', padding: '2px 8px', borderRadius: 12 }}>
                Executando...
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {onRerun && !isRunningScript && (
              <button className="titlebar-btn" title="Reexecutar comando" onClick={onRerun}>
                <Play size={13} />
              </button>
            )}
            <button className="titlebar-btn" title="Copiar saída" onClick={handleCopy}>
              {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
            </button>
            {!customContent && (
              <button
                className={`titlebar-btn ${loading ? 'animate-spin' : ''}`}
                title="Recarregar logs"
                onClick={loadLogs}
              >
                <RefreshCw size={14} />
              </button>
            )}
            <button className="titlebar-btn" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        <div style={{ padding: 16, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className="log-terminal" style={{ flex: 1, maxHeight: '65vh', whiteSpace: 'pre-wrap', fontFamily: 'Consolas, monospace', fontSize: 12 }}>
            {logs}
          </div>
        </div>
      </div>
    </div>
  )
}
