import React from 'react'

interface StatusBadgeProps {
  running: boolean
  ayugramRunning: boolean
  loading: boolean
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ running, ayugramRunning, loading }) => {
  if (loading) {
    return (
      <div className="status-badge starting">
        <span className="dot-indicator" />
        <span>Verificando...</span>
      </div>
    )
  }

  if (!running) {
    return (
      <div className="status-badge offline">
        <span className="dot-indicator" />
        <span>Container Desconectado</span>
      </div>
    )
  }

  if (ayugramRunning) {
    return (
      <div className="status-badge online">
        <span className="dot-indicator" />
        <span>AyuGram Ativo</span>
      </div>
    )
  }

  return (
    <div className="status-badge starting">
      <span className="dot-indicator" />
      <span>Docker Online (AyuGram Parado)</span>
    </div>
  )
}
