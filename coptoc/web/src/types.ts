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
  status: RosterStatus; basis: 'present' | 'in_area' | 'assigned'; checkin_requested_at: string | null
  deliveries: { channel: 'sms' | 'chat'; status: 'sent' | 'simulated' | 'failed'; at: string; error: string | null }[]
  method: string | null; attempts: number; last_attempt_at: string | null; updated_by: string | null; updated_at: string | null; note: string | null
}
export interface Incident {
  id: string; title: string; kind: 'site' | 'threat' | 'manual'; location_id: string | null; threat_id: string | null; lat: number; lon: number; radius_km: number
  status: 'open' | 'closed'; opened_by: string; opened_at: string; closed_at: string | null; notes: string | null
  total: number; accounted: number; pct: number; counts: Record<RosterStatus, number>; checkins_requested: number
  channels: string[]; delivery_summary: Record<string, { sent: number; simulated: number; failed: number }>; roster: RosterEntry[]
}
export interface Trip {
  id: string; person_id: string; person_name: string; is_vip: boolean
  origin_location_id: string; origin_name: string; origin_lat: number; origin_lon: number
  dest_location_id: string | null; dest_name: string; dest_lat: number; dest_lon: number
  depart_at: string; return_at: string; purpose: string; status: 'planned' | 'active' | 'complete'
  event_id: string | null; created_by: string; source: string
}
export interface CopEvent {
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
  open_incidents: number; unaccounted: number; posture: Posture
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
export interface Snapshot {
  generated_at: string; restricted_included: boolean; restricted_denied: boolean; role: string; watch: Watch; estimates: Estimate[]; summary: Summary; locations: Location[]; teams: Team[]
  people: Person[]; trips: Trip[]; events: CopEvent[]; threats: Threat[]; pirs: PIR[]; assessments: Assessment[]; incidents: Incident[]; log: LogEntry[]
}
export type Selection =
  | { type: 'location'; id: string } | { type: 'person'; id: string } | { type: 'threat'; id: string } | { type: 'event'; id: string } | { type: 'incident'; id: string } | null
export interface Layers { locations: boolean; travelers: boolean; threats: boolean; routes: boolean; events: boolean; residences: boolean }
