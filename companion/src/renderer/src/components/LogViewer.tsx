import React, { useState, useEffect } from 'react'
import { X, RefreshCw, Copy, Check } from 'lucide-react'

interface LogViewerProps {
  isOpen: boolean
  onClose: () => void
  fetchLogs: (lines?: number) => Promise<string>
}

export const LogViewer: React.FC<LogViewerProps> = ({ isOpen, onClose, fetchLogs }) => {
  const [logs, setLogs] = useState<string>('Carregando logs...')
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const loadLogs = async () => {
    setLoading(true)
    const res = await fetchLogs(150)
    setLogs(res || 'Nenhum log encontrado.')
    setLoading(false)
  }

  useEffect(() => {
    if (isOpen) {
      loadLogs()
    }
  }, [isOpen])

  const handleCopy = () => {
    navigator.clipboard.writeText(logs)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header" style={{ padding: '14px 18px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
            Logs de Runtime (AyuGram / Docker)
          </h3>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <button className="titlebar-btn" title="Copiar logs" onClick={handleCopy}>
              {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
            </button>
            <button
              className={`titlebar-btn ${loading ? 'animate-spin' : ''}`}
              title="Recarregar logs"
              onClick={loadLogs}
            >
              <RefreshCw size={14} />
            </button>
            <button className="titlebar-btn" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        <div style={{ padding: 16, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div className="log-terminal" style={{ flex: 1, maxHeight: '60vh' }}>
            {logs}
          </div>
        </div>
      </div>
    </div>
  )
}
