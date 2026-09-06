import type { Graphic, GraphicType, AreaRating, Tasking, UploadPreview, Me, UserInfo, SettingInfo, AreaAssessment, Distribution, Warning, Planning, ImportResult, Operation, Intsum, IntsumHead, Case, CaseDetail, CaseEntity, Queue, Report, Snapshot, Location } from './types'

import type { Brief, Coverage, Plan, Requirement, Role, SourceInfo, Watch } from './types'

// Demo identity. Production: from the session. Decision C — only battle_captain and ep may see the restricted layer.
export const session = { role: 'battle_captain' as Role, actor: '', userId: (() => { try { return localStorage.getItem('toc.user') || 'u_battle_captain' } catch { return 'u_battle_captain' } })() }
const ROLE_LABEL: Record<Role, string> = { battle_captain: 'Battle Captain', ep: 'Executive Protection', security: 'Security', analyst: 'S2 Analyst', ea: 'Executive Assistant', logistics: 'S4 Logistics', signal: 'S6 Signal' }
const actor = () => `${ROLE_LABEL[session.role]} (web)`

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-TOC-Actor': actor(), 'X-TOC-Role': session.role, ...(session.userId ? { 'X-TOC-User': session.userId } : {}) }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status} ${(await r.text()).slice(0, 200)}`)
  return r.json()
}

export const fetchSnapshot = (restricted: boolean) => req<Snapshot>('GET', `/v1/cop/snapshot?restricted=${restricted}`)
export const confirmLink = (threatId: string, target_type: 'location' | 'person', target_id: string, note?: string) =>
  req<{ link_id: number; status: string }>('POST', `/v1/cop/threats/${threatId}/links`, { target_type, target_id, note })
export const removeLink = (threatId: string, linkId: number) => req<unknown>('DELETE', `/v1/cop/threats/${threatId}/links/${linkId}`)
/** §3.1 sites: add one, correct one, and move the TOC. Home station stays whatever site is typed "hq". */
export const createLocation = (body: Partial<Location> & { name: string; lat: number; lon: number }) => req<{ id: string }>('POST', '/v1/cop/locations', body)
export const updateLocation = (id: string, body: Partial<Location>) => req<{ id: string; changed: string[] }>('PATCH', `/v1/cop/locations/${id}`, body)
export const setToc = (id: string) => req<unknown>('POST', `/v1/cop/locations/${id}/toc`, {})

export const setPosture = (locationId: string, posture: string, reason: string) => req<unknown>('PATCH', `/v1/cop/locations/${locationId}/posture`, { posture, reason })
export const draftAssessment = (subject_type: string, subject_id: string) => req<{ id: string; refused: boolean; confidence: string }>('POST', '/v1/cop/assessments/draft', { subject_type, subject_id })
export const setAssessmentStatus = (id: string, status: string) => req<unknown>('PATCH', `/v1/cop/assessments/${id}`, { status })
export const setPirStatus = (id: string, status: string) => req<unknown>('PATCH', `/v1/cop/pirs/${id}`, { status })
export const refreshIntel = () => req<{ sources: { source: string; ok: boolean; collected?: number; created?: number; updated?: number; error?: string }[]; collected: number; created: number; updated: number; failed: string[] }>('POST', '/v1/cop/intel/refresh')
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
export const listCases = () => req<Case[]>('GET', '/v1/s2/cases')
export const openCase = (body: { title: string; kind: string; subject_type?: string; subject_id?: string; summary?: string }) => req<Case>('POST', '/v1/s2/cases', body)
export const getCase = (id: string) => req<CaseDetail>('GET', `/v1/s2/cases/${id}`)
export const getQueue = (id: string) => req<Queue>('GET', `/v1/s2/cases/${id}/queue`)
export const decide = (caseId: string, kind: 'entity' | 'relationship' | 'event', id: string, decision: 'confirm' | 'reject', note?: string) => req<{ status: string }>('POST', `/v1/s2/cases/${caseId}/decide`, { kind, id, decision, note })
export const mergeEntity = (caseId: string, id: string, into: string) => req<CaseEntity>('POST', `/v1/s2/cases/${caseId}/entities/${id}/merge`, { into })
export const closeCase = (id: string) => req<Case>('PATCH', `/v1/s2/cases/${id}/close`)
export const fileReport = (body: { text: string; kind: string; reported_by: string; reporter_role?: string; place?: string; case_id?: string; lat?: number; lon?: number }) => req<Report & { extracted: { entities: number; relationships: number; events: number } | null }>('POST', '/v1/s2/reports', body)
export const listReports = (caseId?: string) => req<Report[]>('GET', caseId ? `/v1/s2/reports?case_id=${caseId}` : '/v1/s2/reports')
export const listAreas = () => req<AreaAssessment[]>('GET', '/v1/s2/area-assessments')
export const getArea = (id: string) => req<AreaAssessment>('GET', `/v1/s2/area-assessments/${id}`)
export const draftArea = (requirement_ids: string[], title?: string) => req<AreaAssessment>('POST', '/v1/s2/area-assessments', { requirement_ids, title })
export const setAreaStatus = (id: string, status: 'draft' | 'review' | 'approved') => req<AreaAssessment>('PATCH', `/v1/s2/area-assessments/${id}`, { status })
export const listIntsums = () => req<IntsumHead[]>('GET', '/v1/s2/intsum')
export const latestIntsum = () => req<Intsum>('GET', '/v1/s2/intsum/latest')
export const getIntsum = (id: string) => req<Intsum>('GET', `/v1/s2/intsum/${id}`)
export const draftIntsum = () => req<Intsum>('POST', '/v1/s2/intsum/draft')
export const releaseIntsum = (id: string, notes?: string) => req<Intsum>('POST', `/v1/s2/intsum/${id}/release`, { notes })
export const addToRoster = (incidentId: string, body: { person_id?: string; name?: string; phone?: string; role?: string; note?: string }) => req<{ person_id: string; name: string }>('POST', `/v1/cop/incidents/${incidentId}/roster`, body)
export const listOperations = () => req<Operation[]>('GET', '/v1/cop/operations')
export const getOperation = (id: string) => req<Operation>('GET', `/v1/cop/operations/${id}`)
export const openOperation = (body: { subject_type: string; subject_id: string; title?: string; from_assessment_id?: string; from_area_id?: string; notes?: string }) => req<Operation>('POST', '/v1/cop/operations', body)
export const setOperationStatus = (id: string, status: string, notes?: string) => req<Operation>('PATCH', `/v1/cop/operations/${id}`, { status, notes })
export const addTask = (opId: string, body: { title: string; section: string; owner?: string }) => req<unknown>('POST', `/v1/cop/operations/${opId}/tasks`, body)
export const updateTask = (opId: string, taskId: string, body: { status?: string; owner?: string; note?: string }) => req<unknown>('PATCH', `/v1/cop/operations/${opId}/tasks/${taskId}`, body)
export const requestResource = (opId: string, body: { item: string; qty: number; note?: string }) => req<unknown>('POST', `/v1/cop/operations/${opId}/resources`, body)
export const answerResource = (opId: string, resId: string, status: string, note?: string) => req<unknown>('PATCH', `/v1/cop/operations/${opId}/resources/${resId}`, { status, note })
export const getDistribution = (ptype: string, pid: string) => req<Distribution>('GET', `/v1/s2/products/${ptype}/${pid}/distribution`)
export const disseminate = (ptype: string, pid: string, recipients: string[], channel: 'wall' | 'chat' = 'wall') => req<Distribution>('POST', `/v1/s2/products/${ptype}/${pid}/disseminate`, { recipients, channel })
export const ackProduct = (ptype: string, pid: string) => req<Distribution>('POST', `/v1/s2/products/${ptype}/${pid}/ack`)
export const listWarnings = (status?: string) => req<Warning[]>('GET', status ? `/v1/s2/warnings?status=${status}` : '/v1/s2/warnings')
export const draftWarning = (body: { subject_type: string; subject_id: string; title: string; text?: string; severity?: string; threat_id?: string }) => req<Warning>('POST', '/v1/s2/warnings', body)
export const suggestWarnings = () => req<{ suggested: Warning[] }>('POST', '/v1/s2/warnings/suggest')
export const releaseWarning = (id: string) => req<Warning>('POST', `/v1/s2/warnings/${id}/release`)
export const cancelWarning = (id: string) => req<Warning>('POST', `/v1/s2/warnings/${id}/cancel`)
export const getPlanning = (days = 90) => req<Planning>('GET', `/v1/cop/planning?days=${days}`)
export const assignCoverage = (eventId: string, person_id: string, role: string) => req<{ overlaps: string[] }>('POST', `/v1/cop/events/${eventId}/coverage`, { person_id, role })
export const removeCoverage = (eventId: string, personId: string) => req<unknown>('DELETE', `/v1/cop/events/${eventId}/coverage/${personId}`)
export const setRequiredSecurity = (eventId: string, required_security: number) => req<unknown>('PATCH', `/v1/cop/events/${eventId}`, { required_security })
export const importText = (kind: 'people' | 'shifts' | 'trips' | 'ics' | 'legs' | 'itinerary', text: string) => req<ImportResult>('POST', `/v1/cop/import/${kind}`, { text })

// §7 / §8 — the background boards
export const updateSupply = (id: string, body: { on_hand?: number; required?: number; note?: string }) => req<{ id: string }>('PATCH', `/v1/cop/supply/${id}`, body)
export const updateShipment = (id: string, body: { status?: string; eta?: string; priority?: string; note?: string }) => req<{ id: string }>('PATCH', `/v1/cop/shipments/${id}`, body)
export const updateSystem = (id: string, body: { status?: string; pace?: string; note?: string }) => req<{ id: string }>('PATCH', `/v1/cop/systems/${id}`, body)

// §11.3 — settings entered from the wall (Battle Captain); values are write-only
export const listSettings = () => req<{ settings: SettingInfo[]; note: string }>('GET', '/v1/cop/settings')
export const putSetting = (name: string, value: string) => req<SettingInfo>('PUT', `/v1/cop/settings/${name}`, { value })
export const clearSetting = (name: string) => req<SettingInfo>('DELETE', `/v1/cop/settings/${name}`)
export const setProfile = (profile: 'military' | 'corporate') => req<{ profile: string; dataset: string }>('PUT', '/v1/cop/profile', { profile })

// §9 users and permissions
export const me = () => req<Me>('GET', '/v1/cop/me')
export const listUsers = () => req<{ users: UserInfo[]; presets: Record<string, { label: string; perms: Record<string, string>; battle_captain: boolean }>; sections: string[] }>('GET', '/v1/cop/users')
export const createUser = (body: Partial<UserInfo>) => req<UserInfo>('POST', '/v1/cop/users', body)
export const updateUser = (id: string, body: Omit<Partial<UserInfo>, 'perms'> & { perms?: Record<string, string | null> }) => req<UserInfo>('PATCH', `/v1/cop/users/${id}`, body)
export const deleteUser = (id: string) => req<{ id: string }>('DELETE', `/v1/cop/users/${id}`)
export const signIn = (userId: string) => { session.userId = userId; try { localStorage.setItem('toc.user', userId) } catch { /* private mode */ } }

// §13 the spreadsheet upload: preview → mapping → commit
export const uploadPreview = async (section: string, file: File): Promise<UploadPreview> => {
  const fd = new FormData(); fd.append('file', file)
  const r = await fetch(`/v1/cop/upload/${section}/preview`, { method: 'POST', body: fd, headers: { 'X-TOC-Actor': actor(), 'X-TOC-Role': session.role, ...(session.userId ? { 'X-TOC-User': session.userId } : {}) } })
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 200)}`)
  return r.json()
}
export const uploadCommit = (section: string, body: { upload_id: string; sheet: string; mapping: Record<string, string | null>; kind?: string }) => req<ImportResult & { section: string; sheet: string }>('POST', `/v1/cop/upload/${section}/commit`, body)

// §3.4 the graphics object
export const graphicsCatalog = () => req<{ profile: string; types: GraphicType[] }>('GET', '/v1/cop/graphics/catalog')
export const drawGraphic = (body: { type: string; kind: string; name: string; geometry: unknown; window_from?: string; window_to?: string; status?: string; note?: string; subject_type?: string; subject_id?: string }) => req<Graphic>('POST', '/v1/cop/graphics', body)
export const updateGraphic = (id: string, body: { name?: string; geometry?: unknown; window_from?: string | null; window_to?: string | null; status?: string; note?: string }) => req<Graphic>('PATCH', `/v1/cop/graphics/${id}`, body)

// §5.6a the rated area assessment
export const areaIndicators = () => req<{ profile: string; indicators: { id: string; label: string }[] }>('GET', '/v1/cop/areas/indicators')
export const listAreaRatings = (all = false) => req<AreaRating[]>('GET', `/v1/cop/areas${all ? '?all=true' : ''}`)
export const assessArea = (body: { place?: string; location_id?: string; lat?: number; lon?: number; summary?: string; ratings: { indicator: string; rating: string; note: string }[] }) => req<AreaRating>('POST', '/v1/cop/areas', body)
export const amendArea = (id: string, body: { summary?: string; ratings?: { indicator: string; rating: string; note: string }[] }) => req<AreaRating>('PATCH', `/v1/cop/areas/${id}`, body)

// §5.10 taskings
export const raiseTasking = (body: Partial<Tasking> & { title: string; from_section: string; to_section: string }) => req<Tasking>('POST', '/v1/cop/taskings', body)
export const updateTasking = (id: string, body: Partial<Pick<Tasking, 'status' | 'result' | 'notes' | 'asset' | 'priority' | 'window_from' | 'window_to'>>) => req<Tasking>('PATCH', `/v1/cop/taskings/${id}`, body)
