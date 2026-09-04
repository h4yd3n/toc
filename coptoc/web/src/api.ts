import type { Snapshot } from './types'

import type { Brief, Coverage, Plan, Requirement, Role, SourceInfo, Watch } from './types'

// Demo identity. Production: from the session. Decision C — only battle_captain and ep may see the restricted layer.
export const session = { role: 'battle_captain' as Role }
const ROLE_LABEL: Record<Role, string> = { battle_captain: 'Battle Captain', ep: 'Executive Protection', security: 'Security', analyst: 'S2 Analyst', ea: 'Executive Assistant' }
const actor = () => `${ROLE_LABEL[session.role]} (web)`

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-TOC-Actor': actor(), 'X-TOC-Role': session.role }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status} ${(await r.text()).slice(0, 200)}`)
  return r.json()
}

export const fetchSnapshot = (restricted: boolean) => req<Snapshot>('GET', `/v1/cop/snapshot?restricted=${restricted}`)
export const confirmLink = (threatId: string, target_type: 'location' | 'person', target_id: string, note?: string) =>
  req<{ link_id: number; status: string }>('POST', `/v1/cop/threats/${threatId}/links`, { target_type, target_id, note })
export const removeLink = (threatId: string, linkId: number) => req<unknown>('DELETE', `/v1/cop/threats/${threatId}/links/${linkId}`)
export const setPosture = (locationId: string, posture: string, reason: string) => req<unknown>('PATCH', `/v1/cop/locations/${locationId}/posture`, { posture, reason })
export const draftAssessment = (subject_type: string, subject_id: string) => req<{ id: string; refused: boolean; confidence: string }>('POST', '/v1/cop/assessments/draft', { subject_type, subject_id })
export const setAssessmentStatus = (id: string, status: string) => req<unknown>('PATCH', `/v1/cop/assessments/${id}`, { status })
export const setPirStatus = (id: string, status: string) => req<unknown>('PATCH', `/v1/cop/pirs/${id}`, { status })
export const refreshIntel = () => req<{ collected: number; created: number; updated: number }>('POST', '/v1/cop/intel/refresh')
export const openRollCall = (target: { location_id?: string; threat_id?: string; title?: string; notes?: string }) =>
  req<{ id: string; roster: number }>('POST', '/v1/cop/incidents', target)
export const updateRoster = (incidentId: string, personId: string, status: string, note?: string) =>
  req<unknown>('PATCH', `/v1/cop/incidents/${incidentId}/roster/${personId}`, { status, method: 'call', note })
export const closeIncident = (incidentId: string, notes?: string) => req<unknown>('PATCH', `/v1/cop/incidents/${incidentId}/close`, { notes })
export const requestCheckins = (incidentId: string) => req<{ requested: number; simulated: boolean }>('POST', `/v1/cop/incidents/${incidentId}/request-checkins`)
export const checkInByToken = (token: string, note?: string) => req<{ cleared_rosters: string[] }>('POST', `/v1/cop/checkin/${token}`, note ? { note } : undefined)
export const checkIn = (personId: string, lat: number, lon: number, note: string) => req<{ cleared_rosters: string[] }>('POST', `/v1/cop/people/${personId}/checkin`, { lat, lon, note })
export const getBrief = () => req<Brief>('GET', '/v1/cop/watch/brief')
export const takeWatch = (battle_captain: string) => req<Watch>('POST', '/v1/cop/watch/take', { battle_captain })
export const handover = (notes: string, nstr: boolean) => req<Brief>('POST', '/v1/cop/watch/handover', { notes: notes || undefined, nstr })
export const acknowledge = (battle_captain: string, acknowledged_item_ids: string[]) => req<{ now_holding: Watch }>('POST', '/v1/cop/watch/acknowledge', { battle_captain, acknowledged_item_ids })
export const setEstimate = (section: string, assessment: string, recommendation: string) => req<unknown>('PATCH', `/v1/cop/watch/estimate/${section}`, { assessment, recommendation })
export const listRequirements = (status = 'active') => req<Requirement[]>('GET', `/v1/s2/requirements?status=${status}`)
export const getPlan = (id: string) => req<Plan>('GET', `/v1/s2/requirements/${id}/plan`)
export const getCoverage = () => req<Coverage>('GET', '/v1/s2/coverage')
export const createDirected = (body: { place: string; lat: number; lon: number; window_from?: string; window_to?: string; purpose: string; priority: number }) => req<Requirement>('POST', '/v1/s2/requirements', body)
export const updateRequirement = (id: string, body: { status?: string; priority?: number; indicators?: string[] }) => req<Requirement>('PATCH', `/v1/s2/requirements/${id}`, body)
export const listSources = () => req<SourceInfo[]>('GET', '/v1/s2/sources')
export const updateSource = (id: string, body: { enabled?: boolean; cadence?: string; reliability?: string }) => req<SourceInfo>('PATCH', `/v1/s2/sources/${id}`, body)
