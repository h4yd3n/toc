export type Posture = 'normal' | 'elevated' | 'critical'
export type Severity = 'low' | 'moderate' | 'elevated' | 'critical'
export type LocationType = 'hq' | 'office' | 'datacenter' | 'residence' | 'venue'
export type Confidence = 'low' | 'moderate' | 'high' | 'insufficient'

export interface Location {
  id: string; name: string; type: LocationType; lat: number; lon: number
  city: string; country: string; posture: Posture; effective_posture: Posture; sensitivity: 'standard' | 'restricted'
  assigned: number; present: number; security_on_shift: number; vips_present: number
  threat_ids_in_area: string[]; confirmed_threat_ids: string[]
}
export interface Team { id: string; name: string; location_id: string; function: string; is_security: boolean }
export interface Person {
  id: string; name: string; role: string; team_id: string; team_name: string
  home_location_id: string; location_id: string | null; is_vip: boolean
  on_shift: boolean; shift_role: string | null; status: 'at_post' | 'traveling'
  lat: number; lon: number; trip_id: string | null
  position_source: 'derived' | 'checkin'; checkin_age_h: number | null; checkin_stale: boolean
  last_checkin_at: string | null; last_checkin_note: string | null
  threat_ids_in_area: string[]; confirmed_threat_ids: string[]
  phone: string | null; email: string | null; source: string; incident_status: RosterStatus | null
}
export type RosterStatus = 'unaccounted' | 'contacted' | 'safe' | 'injured' | 'assist' | 'unreachable'
export interface RosterEntry {
  person_id: string; name: string; role: string; is_vip: boolean; phone: string | null; email: string | null
  status: RosterStatus; basis: 'present' | 'in_area' | 'assigned' | 'manual'; checkin_requested_at: string | null
  deliveries: { channel: 'sms' | 'chat'; status: 'sent' | 'simulated' | 'failed'; at: string; error: string | null }[]
  method: string | null; attempts: number; last_attempt_at: string | null; updated_by: string | null; updated_at: string | null; note: string | null
}
export interface Incident {
  id: string; title: string; kind: 'site' | 'threat' | 'manual'; location_id: string | null; threat_id: string | null; lat: number; lon: number; radius_km: number
  status: 'open' | 'closed'; opened_by: string; opened_at: string; closed_at: string | null; notes: string | null
  total: number; accounted: number; pct: number; counts: Record<RosterStatus, number>; checkins_requested: number
  channels: string[]; delivery_summary: Record<string, { sent: number; simulated: number; failed: number }>; roster: RosterEntry[]
}
export interface Trip { operation?: OperationSummary | null;
  id: string; person_id: string; person_name: string; is_vip: boolean
  origin_location_id: string; origin_name: string; origin_lat: number; origin_lon: number
  dest_location_id: string | null; dest_name: string; dest_lat: number; dest_lon: number
  depart_at: string; return_at: string; purpose: string; status: 'planned' | 'active' | 'complete'
  event_id: string | null; created_by: string; source: string
}
export interface CopEvent { operation?: OperationSummary | null;
  id: string; name: string; event_type: string; venue_location_id: string | null
  venue_name: string; venue_lat: number; venue_lon: number; start_at: string; end_at: string
  status: 'upcoming' | 'active' | 'past'; days_until: number; description: string; security_plan: string | null
  attendee_ids: string[]; attendee_count: number; vip_count: number; security_count: number; trips_generated: number
  threat_ids_in_area: string[]; source: string
}
export interface LinkTarget { target_type: 'location' | 'person'; target_id: string; target_name: string }
export interface ConfirmedLink extends LinkTarget { link_id: number; confirmed_by: string; confirmed_at: string; note: string | null }
export interface Threat {
  id: string; external_id: string | null; title: string; summary: string; lat: number; lon: number; radius_km: number
  severity: Severity; event_type: string | null; source: string; url: string | null; confidence: 'low' | 'moderate' | 'high'
  observed_at: string; synthetic: boolean; suggested_targets: LinkTarget[]; confirmed_links: ConfirmedLink[]
}
export interface PIR { id: string; question: string; status: string; owner: string; priority: number; subject_type: string | null; subject_id: string | null; created_at: string; expires_at: string | null }
export interface Judgment { claim: string; likelihood: string; band: string; confidence: string }
export interface Evidence { threat_id: string; title: string; source: string; confidence: string; severity: Severity; distance_km: number; confirmed: boolean; synthetic: boolean }
export interface Assessment {
  id: string; title: string; subject_type: string; subject_id: string; likelihood: string; band: string; confidence: Confidence
  bluf: string; key_judgments: Judgment[]; evidence: Evidence[]; gaps: string[]; author: string
  status: 'draft' | 'review' | 'approved' | 'superseded'; created_at: string; approved_by: string | null; approved_at: string | null
}
export interface LogEntry { id: string; at: string; type: string; actor: string; actor_type: string; subject: string; old: string | null; new: string | null; summary: string | null }
export interface Summary {
  total_people: number; present: number; traveling: number; vips_traveling: number; security_on_shift: number
  active_threats: number; real_threats: number; confirmed_links: number; checked_in_fresh: number; open_pirs: number; upcoming_events: number
  open_incidents: number; unaccounted: number; flash: number; warnings_pending: number; posture: Posture
}
export type Role = 'battle_captain' | 'ep' | 'security' | 'analyst' | 'ea'
export interface Watch {
  id: string; name: string; battle_captain: string | null; status: 'open' | 'pending_ack' | 'handed_over'
  started_at: string; ends_at: string; elapsed_h: number; remaining_h: number; overdue: boolean; in_overlap: boolean; overlap_minutes: number
  next_watch: string; next_starts_at: string; pattern: string; nstr: boolean; outgoing_notes: string | null
  handed_over_at: string | null; acknowledged_by: string | null; acknowledged_at: string | null
}
export interface Estimate { section: 'S1' | 'S2' | 'S3' | 'S6'; assessment: string; recommendation: string; updated_by: string | null; updated_at: string | null }
export interface BriefEvent { id: string; at: string; type: string; actor: string; subject: string; summary: string | null; old: string | null; new: string | null; during_handover: boolean }
export interface Brief {
  watch: Watch; window: { from: string; to: string; overlap_from: string }
  significant_events: Record<string, BriefEvent[]>; event_count: number
  current_status: { estimates: Estimate[]; posture: Posture; open_incidents: { id: string; title: string; accounted: number; total: number }[]; unaccounted: number
    travelers: { id: string; name: string; where: string; checkin: boolean }[]; assessments_in_review: { id: string; title: string }[]
    open_pirs: { id: string; question: string }[]; stale_checkins: { id: string; name: string }[] }
  next_shift: { watch: string; from: string; to: string; events_starting: { id: string; name: string; venue: string; start_at: string }[]
    trips_departing: { id: string; who: string; to: string; at: string }[]; trips_returning: { id: string; who: string; from: string; at: string }[]
    pirs_expiring: { id: string; question: string; expires_at: string }[] }
  handover_items: ({ kind: 'open_incident'; id: string; title: string; accounted: number; total: number } | { kind: 'during_handover'; id: string; summary: string; at: string })[]
  outgoing_notes: string | null; nstr: boolean; acknowledgement: { required_item_ids: string[]; by: string | null; at: string | null }; generated_at: string
}
export interface Snapshot { warnings: Warning[];
  generated_at: string; restricted_included: boolean; restricted_denied: boolean; role: string; watch: Watch; estimates: Estimate[]; summary: Summary; locations: Location[]; teams: Team[]
  people: Person[]; trips: Trip[]; events: CopEvent[]; threats: Threat[]; pirs: PIR[]; assessments: Assessment[]; incidents: Incident[]; log: LogEntry[]
}
export type Selection =
  | { type: 'location'; id: string } | { type: 'person'; id: string } | { type: 'threat'; id: string } | { type: 'event'; id: string } | { type: 'incident'; id: string } | null
export interface Layers { locations: boolean; travelers: boolean; threats: boolean; routes: boolean; events: boolean; residences: boolean }

export interface Requirement {
  id: string; kind: 'standing' | 'directed'; subject_type: 'location' | 'trip' | 'event' | 'person' | 'place'; subject_id: string | null; subject_name: string
  lat: number; lon: number; radius_km: number; question: string; purpose: string; priority: number; window_from: string | null; window_to: string | null
  status: 'active' | 'answered' | 'expired'; owner: string; indicators: string[]; created_at: string; updated_at: string
  coverage: { covered: number; total: number; pct: number; gaps: string[] }
}
export interface PlanRow { indicator: string; label: string; covered: boolean; sources: { id: string; name: string; reliability: string; cadence: string }[]; recommended: { id: string; name: string; access: string; reliability: string; built: boolean }[] }
export interface Plan { requirement_id: string; indicators: PlanRow[]; covered: number; total: number; gaps: string[]; coverage_pct: number }
export interface Coverage { requirements: number; fully_covered: number; avg_coverage_pct: number; gaps: { indicator: string; label: string; requirements_affected: number; recommended_sources: { id: string; name: string; access: string; built: boolean }[] }[] }
export interface SourceInfo { id: string; name: string; indicators: string[]; access: string; reliability: string; cadence: string; built: boolean; enabled: boolean; configured: boolean; last_collected_at: string | null; last_result: string | null; cadences: string[] }

// §5.10 / §5.11 — organic reports and the case graph
export interface Evidence { report_id: string; quote: string; source: string; reliability: string; credibility: number; at: string | null }
export interface CaseEntity { id: string; type: string; name: string; aliases: string[]; status: 'suggested' | 'confirmed' | 'rejected'; evidence: Evidence[]; decided_by: string | null }
export interface CaseRel { id: string; from: string; to: string; type: string; status: 'suggested' | 'confirmed' | 'rejected'; grade: string; evidence: Evidence[]; from_name?: string; to_name?: string; first_seen: string | null; last_seen: string | null }
export interface CaseEvent { id: string; at: string | null; place: string | null; type: string; summary: string; participants: string[]; status: 'suggested' | 'confirmed' | 'rejected'; evidence: Evidence[] }
export interface Report { id: string; kind: string; reported_by: string; reporter_role: string; at: string; place: string | null; text: string; case_id: string | null; grade: string; source: string }
export interface Case { id: string; title: string; kind: 'general' | 'person' | 'site' | 'actor'; subject_type: string | null; subject_id: string | null; summary: string; status: 'open' | 'closed'
  opened_by: string; opened_at: string; closed_at: string | null; access_roles: string[]; entities?: number; relationships?: number; events?: number; pending_review?: number }
export interface CaseDetail extends Case { graph: { entities: CaseEntity[]; relationships: CaseRel[]; events: CaseEvent[] }; reports: Report[]; analysis: { links: string[]; pattern: string } }
export interface Queue { case_id: string; entities: CaseEntity[]; relationships: CaseRel[]; events: CaseEvent[]; total: number }

// §5.6 Area Assessment — candidates side by side, no composite
export interface AreaCell { indicator: string; label: string; state: 'reported' | 'quiet' | 'gap' | 'facts'; facts?: { date: string; name: string; local_name: string; national: boolean }[]; note?: string | null; likelihood: string | null; band: string | null; confidence: string | null
  confidence_basis: string[]; evidence: { threat_id: string; title: string; source: string; severity: string; distance_km: number; observed_at: string; synthetic: boolean }[]; sources: string[]; recommended?: string[]; worst?: string; severity?: string }
export interface AreaCandidate { requirement_id: string; place: string; lat: number; lon: number; window_from: string | null; window_to: string | null; cells: AreaCell[]
  counts: { reported: number; quiet: number; gap: number; facts?: number }; worst: { indicator: string; label: string; likelihood: string; band: string; confidence: string; title: string } | null; known: boolean; bluf: string; author: string
  unclassified: { threat_id: string; title: string }[] }
export interface AreaAssessment { id: string; title: string; purpose: string; requirement_ids: string[]; status: 'draft' | 'review' | 'approved'; author: string; created_at: string; decided_by: string | null
  indicators: { id: string; label: string }[]; candidates: AreaCandidate[]; gaps: string[]; approvable: boolean; refusal: string | null; note: string; places?: string[] }

// §5.6 INTSUM — the daily diff (Decision G)
export interface LogEv { id: string; at: string; type: string; actor: string; subject: string; summary: string; old: string | null; new: string | null }
export interface Intsum { id: string; status: 'draft' | 'released'; drafted_by: string; drafted_at: string; released_by: string | null; released_at: string | null; notes: string
  period: { from: string; to: string; hours: number }; headline: string; nstr: boolean; structure: string[]; event_count: number
  requirements: { active: number; standing: number; directed: number; created: LogEv[]; updated: LogEv[]; expired: { id: string; subject: string }[]; answered: { id: string; subject: string }[] }
  new_threats: { id: string; title: string; severity: string; source: string; confidence: string; observed_at: string; synthetic: boolean; requirements: { id: string; subject: string; priority: number }[] }[]
  wall: { links: LogEv[]; posture: LogEv[]; roll_calls: LogEv[] }
  reports: { id: string; kind: string; by: string; place: string | null; grade: string; text: string; case_id: string | null }[]
  cases: { opened: LogEv[]; closed: LogEv[]; decisions: number; open: number }
  products: { assessments: LogEv[]; area_assessments: LogEv[]; pending_area_assessments: { id: string; title: string; status: string }[] }
  collection: { runs: LogEv[]; source_changes: LogEv[]; sources: { id: string; name: string; last_collected_at: string | null; last_result: string | null }[]; gaps: { indicator: string; label: string; requirements_affected: number }[] } }
export interface IntsumHead { id: string; status: 'draft' | 'released'; period: { from: string; to: string; hours: number }; headline: string; nstr: boolean; released_by: string | null }

// §5.10 #3 operations, #4 dissemination
export interface OpTask { id: string; title: string; section: string; owner: string; status: 'todo' | 'doing' | 'done' | 'blocked'; due_at: string | null; order: number; updated_by: string | null; updated_at: string | null; note: string }
export interface OpResource { id: string; item: string; qty: number; status: 'requested' | 'approved' | 'issued' | 'denied'; note: string; updated_by: string | null; updated_at: string | null }
export interface OperationSummary { id: string; title: string; subject_type: string; subject_id: string; subject_name: string; status: 'planned' | 'active' | 'complete' | 'cancelled'; tasks_total: number; tasks_done: number; blocked: number; resources_open: number; pct: number; from_product_type: string | null; from_product_id: string | null; opened_by: string }
export interface Operation extends OperationSummary { opened_at: string; closed_at: string | null; notes: string; tasks: OpTask[]; resources: OpResource[] }
export interface Distribution { product_type: string; product_id: string; recipients: { id: string; recipient: string; channel: string; delivery: string; sent_at: string; sent_by: string; acknowledged_at: string | null; acknowledged_by: string | null; latency: { created_to_sent_min: number | null; sent_to_ack_min: number | null; outstanding_min: number | null }; stale: boolean; note: string }[]; sent: number; acknowledged: number; unacknowledged: string[]; stale: string[] }

// §5.6 Warning — FLASH
export interface Warning { id: string; title: string; text: string; subject_type: 'location' | 'person' | 'event'; subject_id: string; subject_name: string; threat_id: string | null; severity: string
  status: 'suggested' | 'draft' | 'released' | 'cancelled' | 'expired'; suggested_by: string; created_at: string; released_by: string | null; released_at: string | null; cancelled_by: string | null
  dispatch: { sms?: { sent: number; simulated: number; failed: number }; chat?: string; people?: number; simulated?: boolean }; recipients: string[]; age_min: number | null }
