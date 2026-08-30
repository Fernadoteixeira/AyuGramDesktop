import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '../components/StatusBadge'

describe('StatusBadge', () => {
  it('renders loading state correctly', () => {
    render(<StatusBadge running={false} ayugramRunning={false} loading={true} />)
    expect(screen.getByText(/Verificando/i)).toBeInTheDocument()
  })

  it('renders offline container state', () => {
    render(<StatusBadge running={false} ayugramRunning={false} loading={false} />)
    expect(screen.getByText(/Container Desconectado/i)).toBeInTheDocument()
  })

  it('renders container running with AyuGram active', () => {
    render(<StatusBadge running={true} ayugramRunning={true} loading={false} />)
    expect(screen.getByText(/AyuGram Ativo/i)).toBeInTheDocument()
  })

  it('renders container running with AyuGram stopped', () => {
    render(<StatusBadge running={true} ayugramRunning={false} loading={false} />)
    expect(screen.getByText(/Docker Online \(AyuGram Parado\)/i)).toBeInTheDocument()
  })
})
