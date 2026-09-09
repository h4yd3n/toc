import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '24px',
          color: '#ef4444',
          background: '#0d1219',
          minHeight: '100vh',
          fontFamily: 'monospace',
          overflow: 'auto',
          boxSizing: 'border-box'
        }}>
          <h2 style={{ color: '#fff', margin: '0 0 16px' }}>TOC Interface Error</h2>
          <div style={{
            background: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.4)',
            padding: '16px',
            borderRadius: '6px',
            marginBottom: '16px'
          }}>
            <strong>{this.state.error?.name}: {this.state.error?.message}</strong>
          </div>
          <pre style={{
            color: '#a0b0c4',
            fontSize: '12px',
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            background: '#070a0f',
            padding: '16px',
            borderRadius: '6px'
          }}>
            {this.state.error?.stack}
            {this.state.errorInfo?.componentStack}
          </pre>
          <button
            onClick={() => { localStorage.clear(); window.location.reload() }}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              background: '#3b82f6',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 700
            }}
          >
            Reset LocalStorage &amp; Reload
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
