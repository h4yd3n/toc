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

// Smoothly reveal ultra-thin scrollbars only while scrolling commences, fading out when idle
window.addEventListener(
  'scroll',
  (e) => {
    const target = e.target as HTMLElement | null
    if (target && target.classList) {
      target.classList.add('is-scrolling')
      clearTimeout((target as any)._scrollTimer)
      ;(target as any)._scrollTimer = window.setTimeout(() => {
        target.classList.remove('is-scrolling')
      }, 900)
    }
  },
  { capture: true, passive: true },
)
