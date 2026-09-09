import type { Graphic, GraphicType, AreaRating, Tasking, UploadPreview, Me, UserInfo, SettingInfo, AreaAssessment, Distribution, Warning, Planning, ImportResult, Operation, Intsum, IntsumHead, Case, CaseDetail, CaseEntity, Queue, Report, Snapshot, Location } from './types'

import type { Brief, Coverage, Plan, Requirement, Role, SourceInfo, Watch } from './types'

// Demo identity. Production: from the session. Decision C — only battle_captain and ep may see the restricted layer.
export const session = { role: 'battle_captain' as Role, actor: '', userId: (() => { try { return (new URLSearchParams(window.location.search).get('embedded') === '1' ? (new URLSearchParams(window.location.search).get('profile') || '__missing_native_profile__') : null) || localStorage.getItem('toc.user') || 'u_battle_captain' } catch { return 'u_battle_captain' } })() }
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
export const updateSystem = (id: string, body: { status?: string; pace?: string | null; note?: string }) => req<{ id: string }>('PATCH', `/v1/cop/systems/${id}`, body)

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

// Staff work: scoped analysis assignments and cited products.
export interface WorkEvidence { context_scopes?: {case_id?: string | null}[]; case_id?: string | null; section?: string; id: string; label: string; text: string }
export interface WorkAnalysis { title: string; summary: string; findings: { claim: string; citations: { source_id: string; quote: string }[]; uncertainty: string }[]; gaps: string[]; proposed_tasks: string[] }
export interface WorkAssignment { location_id: string | null; id: string; section: import('./types').SectionCode; case_id: string | null; instruction: string; status: string; owner: string; cadence_minutes: number; created_at: string; last_success_at: string | null; next_at: string }
export interface WorkRun { instruction?: string; attempts?: number; retry_at?: string | null; original?: WorkAnalysis; metrics?: { seconds?: number; usage?: Record<string,number> }; id: string; assignment_id: string; status: string; review_status: string; revision: number; result: Partial<WorkAnalysis>; evidence: WorkEvidence[]; provider: string; model: string; error: string; reviewed_by: string; created_at: string; completed_at: string | null; history: { at: string; actor: string; action: string; note: string; result?: WorkAnalysis }[] }
export interface WorkBoard { assignments: WorkAssignment[]; runs: WorkRun[]; provider: { provider: string; model: string; configured: boolean; effort: string } }
export const getWork = () => req<WorkBoard>('GET', '/v1/work')
export const assignWork = (body: { section: import('./types').SectionCode; case_id?: string; location_id?: string; instruction: string; cadence_minutes: number }) => req<WorkAssignment>('POST', '/v1/work/assignments', body)
export const changeWork = (id: string, action: 'pause' | 'resume' | 'cancel' | 'run') => req<WorkAssignment>('PATCH', `/v1/work/assignments/${id}`, { action })
export const reviewWork = (id: string, revision: number, action: 'save' | 'review' | 'release' | 'reject', result?: WorkAnalysis, note = '') => req<WorkRun>('PATCH', `/v1/work/runs/${id}`, { revision, action, result, note })
export const editAssessment = (id: string, bluf: string) => req<unknown>('PATCH', `/v1/cop/assessments/${id}`, { bluf })
export const attachReport = (id: string, case_id: string) => req<Report>('POST', `/v1/s2/reports/${id}/attach`, { case_id })
export const createWorkTask = (id: string, index: number, to_section: import('./types').SectionCode) => req<{ id: string; status: string }>('POST', `/v1/work/runs/${id}/taskings`, { index, to_section })
export const createEvent = (body: { name: string; venue_location_id: string; start_at: string; end_at: string; description: string; generate_trips: boolean }) => req<{ id: string }>('POST', '/v1/cop/events', body)
export const getDraft = <T>(section: string, key: string) => req<{ payload: Partial<T>; updated_at: string | null }>('GET', `/v1/work/drafts/${section}/${encodeURIComponent(key)}`)
export const saveDraft = (section: string, key: string, payload: unknown) => req<{ saved: boolean }>('PUT', `/v1/work/drafts/${section}/${encodeURIComponent(key)}`, payload)
export const createSupply = (body: { item: string; location_id: string | null; on_hand: number; required: number; unit: string; note: string }) => req<{id:string}>('POST','/v1/cop/supply',body)
export const createShipment = (body: { description: string; quantity: string; to_location_id: string | null; eta: string; note: string }) => req<{id:string}>('POST','/v1/cop/shipments',body)
export const createSystem = (body: { name: string; location_id: string | null; pace: string | null; status: string; note: string }) => req<{id:string}>('POST','/v1/cop/systems',body)
export const createPerson = (body:{name:string;role:string;team_id:string;email:string;phone:string}) => req<{id:string}>('POST','/v1/cop/people',body)
export const updatePersonAssignment = (id:string,body:{on_shift:boolean;shift_role:string|null}) => req<unknown>('PATCH',`/v1/cop/people/${id}/assignment`,body)

export const editWork = (id:string,instruction:string,cadence_minutes:number) => req<WorkAssignment>('PATCH',`/v1/work/assignments/${id}`,{action:'edit',instruction,cadence_minutes})
export const getActivity = (before?:number,includeReads=false) => req<{items:Snapshot['log'];next_cursor:number|null}>('GET',`/v1/cop/activity?include_reads=${includeReads}${before ? '&before='+before : ''}`)

export type IntakeProposal = {
  id: string; target_id: string | null; status: string; revision: number;
  values: Record<string,string>; original: Record<string,string>; current: Record<string,string | null>;
  questions: string[]; evidence: {field:string;value:string;page:number;quote:string}[];
  history: {at?:string;actor?:string;action:string;note?:string;status?:string;values?:Record<string,string>}[];
}
export type IntakeSubmission = {
  id:string; location_id:string; filename:string; status:string; revision:number; created_at:string;
  owner:string; attempts:number; error:string; pending:number; applied:number;
  meta: {provider?:string;model?:string;gaps?:string[]};
  pages?: {page:number;text:string}[]; proposals?:IntakeProposal[];
}
export const listIntake = () => req<{items:IntakeSubmission[];provider:{configured:boolean;provider:string;model:string}}>('GET','/v1/intake')
export const getIntake = (id:string) => req<IntakeSubmission>('GET',`/v1/intake/${id}`)
export const submitIntakeText = (text:string,location_id:string) => req<IntakeSubmission>('POST','/v1/intake/text',{text,location_id})
export const retryIntake = (id:string) => req<IntakeSubmission>('POST',`/v1/intake/${id}/retry`)
export const reviewIntake = (sid:string,pid:string,body:{revision:number;action:'save'|'apply'|'reject';values?:Record<string,string>;target_id?:string;create_new?:boolean;note?:string}) => req<IntakeProposal>('PATCH',`/v1/intake/${sid}/proposals/${pid}`,body)
export async function submitIntakeFile(file:File,locationId:string):Promise<IntakeSubmission> {
  const body=new FormData(); body.append('file',file); body.append('location_id',locationId)
  const response=await fetch('/v1/intake/file',{method:'POST',body,headers:{'X-TOC-Role':session.role,'X-TOC-Actor':actor(),...(session.userId?{'X-TOC-User':session.userId}:{})}})
  if(!response.ok) throw new Error((await response.text()).slice(0,300))
  return response.json()
}
export async function downloadIntakeSource(id:string) {
  const response=await fetch(`/v1/intake/${id}/source`,{headers:{'X-TOC-Role':session.role,'X-TOC-Actor':actor(),...(session.userId?{'X-TOC-User':session.userId}:{})}})
  if(!response.ok) throw new Error('Source is unavailable to this profile')
  const blob=await response.blob(), url=URL.createObjectURL(blob), link=document.createElement('a')
  link.href=url;link.download=blob.type==='application/pdf'?'Manifest.pdf':'Update.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export type IntakeFinding={id:string;shipment_id:string;location_id:string;title:string;status:string;revision:number;checked_at:string;snoozed_until:string|null;history:{actor:string;action:string;note:string;at:string}[]}
export const getIntakeFindings=()=>req<{rule:string;items:IntakeFinding[]}>('GET','/v1/intake/monitor/findings')
export const decideIntakeFinding=(id:string,revision:number,action:string,note:string)=>req<unknown>('PATCH',`/v1/intake/monitor/findings/${id}`,{revision,action,note})
