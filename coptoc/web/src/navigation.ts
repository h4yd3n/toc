import { useEffect, useState } from 'react'
import type { SectionCode } from './types'
export type Destination = { page: 'cop' | 'workspace' | 'work'; section: SectionCode; tab: string; record: string | null }
const sections = ['S1', 'S2', 'S3', 'S4', 'S6']
export function readDestination(hash = window.location.hash): Destination {
  const [path, query] = hash.replace(/^#\/?/, '').split('?')
  const [page, section, tab] = path.split('/')
  return { page: page === 'workspace' || page === 'work' ? page : 'cop', section: sections.includes(section) ? section as SectionCode : 'S2', tab: tab || 'overview', record: new URLSearchParams(query).get('record') }
}
export function destinationHash(d: Destination) {
  return d.page === 'cop' ? '#/cop' : `#/${d.page}/${d.section}/${d.tab}${d.record ? '?' + new URLSearchParams({ record: d.record }) : ''}`
}
export function useDestination() {
  const [destination, setDestination] = useState(readDestination)
  useEffect(() => { const update = () => setDestination(readDestination()); window.addEventListener('hashchange', update); return () => window.removeEventListener('hashchange', update) }, [])
  const navigate = (next: Partial<Destination>) => { const d = { ...destination, record: null, ...next }; window.location.hash = destinationHash(d); setDestination(d) }
  return { destination, navigate }
}
