import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'maplibre-gl/dist/maplibre-gl.css'
import './index.css'
import App from './App.tsx'
import CheckinPage from './CheckinPage.tsx'
import { ErrorBoundary } from './ErrorBoundary.tsx'

const token = location.pathname.startsWith('/checkin/') ? decodeURIComponent(location.pathname.slice('/checkin/'.length)) : null

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      {token ? <CheckinPage token={token} /> : <App />}
    </ErrorBoundary>
  </StrictMode>,
)

if (new URLSearchParams(window.location.search).get('embedded') === '1') document.documentElement.classList.add('native-workspace')
