# TOC COP Backend Contract

The API the web wall is coded against. The native iOS app (`../ios`) builds against this same
contract — same endpoints, same shapes — so every client shares one backend and one data model.

## Base
- **Base URL:** `http://localhost:8000` in dev (set per environment)
- **Version prefix:** `/v1/cop`
- **Auth:** none in the prototype. Production: `Authorization: Bearer <token>`; restricted-tier sites are filtered server-side by role.
- **Actor:** send `X-TOC-Actor: <name>` on every write. It is recorded on the ledger. Defaults to `watch_floor`.
- **Role:** send `X-TOC-Role: battle_captain | ep | security | analyst | ea`. Only `battle_captain` and `ep` may see the restricted layer (Decision C); other roles asking for it get `restricted_denied: true` and the standard picture.
- **Content-Type:** `application/json`
- **Times:** ISO-8601 UTC with `Z`. Clients render relative ("dep 2d ago").

## The three encoded decisions
| # | Decision | Where it lives |
| :-- | :--- | :--- |
| 1 | **Residences are a restricted layer, off by default.** `GET /snapshot` omits `sensitivity: restricted` sites unless `?restricted=true`. | `service.build_snapshot(include_restricted)` |
| 2 | **Presence is hybrid.** Position is derived (active trip → destination, else team's site). A check-in within **12 h** overrides it (`position_source: "checkin"`); older check-ins are flagged `checkin_stale`. | `service.CHECKIN_FRESH_HOURS` |
| A | **Roll-call roster = everyone in the area now + everyone assigned to the site**, each row tagged `basis: present | in_area | assigned`. Threat/manual roll calls are in-area only. | `open_incident` |
| B | **Check-in requests go to the whole roster at once; a person's own check-in clears their row to SAFE via `app`.** Work by exception. | `request_checkins`, `checkin` |
| C | **Restricted layer is honored only for `battle_captain` and `ep`.** | `service.RESTRICTED_ROLES` |
| 1 | **Check-in requests go out over SMS and chat at once.** Real Twilio / Slack delivery when configured (`.env.example`); otherwise every delivery is recorded and displayed as `simulated` — never claimed as sent. | `cop/comms.py`, `DeliveryRow` |
| 2 | **A roll call may close with names still unaccounted**; the count is recorded on the closing ledger event. | `close_incident` |
| 3 | **Only `battle_captain` may open a roll call** (`403` otherwise). Anyone may work the roster. | `routes.ROLL_CALL_OPENERS` |
| 3 | **Proximity suggests, an analyst confirms.** Anything inside a threat's radius (+5 km) is listed in `threat_ids_in_area` / `suggested_targets`. Only a confirmed link (`POST /threats/{id}/links`) changes `effective_posture` — it can raise a site above its human-set `posture`, never lower it. | `service.SEVERITY_TO_POSTURE`, `ThreatLinkRow` |

## 1. Snapshot — everything the wall needs in one call
`GET /v1/cop/snapshot?restricted=false`

```jsonc
{
  "generated_at": "…Z", "restricted_included": false, "restricted_denied": false, "role": "battle_captain",
  "summary": { "total_people": 97, "present": 92, "traveling": 5, "vips_traveling": 4, "security_on_shift": 7,
               "active_threats": 18, "real_threats": 12, "confirmed_links": 2, "checked_in_fresh": 1,
               "open_pirs": 4, "upcoming_events": 3, "open_incidents": 0, "unaccounted": 0, "posture": "elevated" },
  "locations":   [ { "id", "name", "type",                       // hq | office | datacenter | residence | venue
                     "lat", "lon", "city", "country",
                     "posture", "effective_posture",             // human-set; raised by confirmed links
                     "sensitivity",                              // standard | restricted
                     "assigned", "present", "security_on_shift", "vips_present",
                     "threat_ids_in_area": [], "confirmed_threat_ids": [] } ],
  "teams":       [ { "id", "name", "location_id", "function", "is_security" } ],
  "people":      [ { "id", "name", "role", "team_id", "team_name", "home_location_id", "location_id",
                     "is_vip", "on_shift", "shift_role", "status",           // at_post | traveling
                     "lat", "lon", "trip_id",
                     "position_source",                                      // derived | checkin
                     "checkin_age_h", "checkin_stale", "last_checkin_at", "last_checkin_note",
                     "phone", "email", "source",                             // provenance, e.g. hris:workday
                     "incident_status",                                      // roster status if on an open roll call
                     "threat_ids_in_area": [], "confirmed_threat_ids": [] } ],
  "trips":       [ { "id", "person_id", "person_name", "is_vip", "origin_location_id", "origin_name", "origin_lat", "origin_lon",
                     "dest_location_id", "dest_name", "dest_lat", "dest_lon", "depart_at", "return_at", "purpose",
                     "status",                                               // planned | active (complete omitted)
                     "event_id", "created_by", "source" } ],                 // calendar:google | travel_system:concur | manual:ea | event
  "events":      [ { "id", "name", "event_type", "venue_location_id", "venue_name", "venue_lat", "venue_lon", "start_at", "end_at",
                     "status",                                               // upcoming | active
                     "days_until", "description", "security_plan", "attendee_ids": [], "attendee_count", "vip_count", "security_count",
                     "trips_generated", "threat_ids_in_area": [], "source" } ],
  "threats":     [ { "id", "external_id", "title", "summary", "lat", "lon", "radius_km",
                     "severity",                                             // low | moderate | elevated | critical
                     "event_type", "source", "url", "confidence", "observed_at",
                     "synthetic",                                            // false = came from a live collector
                     "suggested_targets": [ { "target_type", "target_id", "target_name" } ],
                     "confirmed_links":   [ { "link_id", "target_type", "target_id", "target_name", "confirmed_by", "confirmed_at", "note" } ] } ],
  "pirs":        [ { "id", "question", "status", "owner", "priority", "subject_type", "subject_id", "created_at", "expires_at" } ],
  "assessments": [ { "id", "title", "subject_type", "subject_id",
                     "likelihood", "band",                                   // one of seven ICD 203 terms + its fixed band; "—" when refused
                     "confidence",                                           // low | moderate | high | insufficient — computed by code
                     "bluf", "key_judgments": [ { "claim", "likelihood", "band", "confidence" } ],
                     "evidence": [ { "threat_id", "title", "source", "confidence", "severity", "distance_km", "confirmed", "synthetic" } ],
                     "gaps": [], "author",                                   // "ai:<model>" | "rule:heuristic-drafter" | "rule:refuse-to-assess" | a person
                     "status",                                               // draft | review | approved | superseded
                     "created_at", "approved_by", "approved_at" } ],
  "incidents":   [ { "id", "title", "kind", "location_id", "threat_id", "lat", "lon", "radius_km",
                     "status",                                               // open | closed (closed shown for 24 h)
                     "opened_by", "opened_at", "closed_at", "notes",
                     "total", "accounted", "pct", "checkins_requested",
                     "channels": ["sms", "chat"], "delivery_summary": { "sms": { "sent", "simulated", "failed" }, "chat": { … } },
                     "counts": { "unaccounted", "contacted", "safe", "injured", "assist", "unreachable" },
                     "roster": [ { "person_id", "name", "role", "is_vip", "phone", "email", "status",
                                   "basis",                                 // present | in_area | assigned (Decision A)
                                   "checkin_requested_at",                  // set by request-checkins (Decision B)
                                   "deliveries": [ { "channel", "status", "at", "error" } ],  // sms|chat × sent|simulated|failed (Decision 1)
                                   "method", "attempts",
                                   "last_attempt_at", "updated_by", "updated_at", "note" } ] } ],
  "log":         [ { "id", "at", "type", "actor", "actor_type", "subject", "old", "new", "summary", "meta" } ]  // newest first, event types cop.*
}
```

**Derived, never stored:** every person's position/status, every site's counts and `effective_posture`, `threat_ids_in_area`, roster counts. Clients must not recompute these.

## 2. Reads
| Method | Path | Returns |
| :--- | :--- | :--- |
| `GET` | `/locations`, `/locations/{id}` | sites; detail adds `teams[]` (with `people[]`) and `present_people[]` |
| `GET` | `/people?status=`, `/people/{id}` | people; detail adds `trip` |
| `GET` | `/trips`, `/events`, `/events/{id}` | event detail adds `attendees[]` and `trips[]` |
| `GET` | `/threats`, `/pirs`, `/assessments`, `/incidents`, `/incidents/{id}` | |
| `GET` | `/log?limit=50` | the battle log |

## 3. Writes — every one appends a hash-chained ledger event
| Method | Path | Body | Ledger event |
| :--- | :--- | :--- | :--- |
| `POST` | `/trips` | `person_id, origin_location_id, dest_location_id | dest_name+dest_lat+dest_lon, depart_at, return_at, purpose` | `cop.trip.created` |
| `PATCH` / `DELETE` | `/trips/{id}` | partial | `cop.trip.updated` / `cop.trip.cancelled` |
| `POST` | `/events` | `name, event_type, venue_location_id | venue_*, start_at, end_at, description, security_plan, attendee_ids[], generate_trips=true` → generates a planned trip per attendee not already at the venue | `cop.event.created` |
| `PATCH` / `DELETE` | `/events/{id}` | | `cop.event.updated` / `cop.event.cancelled` (removes generated trips) |
| `POST` / `DELETE` | `/events/{id}/attendees[/{person_id}]` | `person_ids[], generate_trips` | `cop.event.attendees_added` / `attendee_removed` |
| `POST` | `/people/{id}/checkin` | `lat, lon, note, at?` — if the person is on an open roster, their row becomes `safe` via `app` (Decision B); response lists `cleared_rosters` | `cop.person.checkin` + `cop.incident.contact` |
| `PATCH` | `/people/{id}/shift` | `on_shift, shift_role` | `cop.person.shift` |
| `PATCH` | `/locations/{id}/posture` | `posture, reason` | `cop.location.posture` |
| `POST` / `DELETE` | `/threats/{id}/links[/{link_id}]` | `target_type, target_id, note` | `cop.threat.link_confirmed` / `link_removed` |
| `POST` / `PATCH` | `/pirs[/{id}]` | `question, priority, subject_type, subject_id, expires_at` / `status` | `cop.pir.created` / `updated` |
| `POST` | `/assessments/draft` | `subject_type (trip|event|location|pir), subject_id` → see §4 | `cop.assessment.drafted` |
| `PATCH` | `/assessments/{id}` | `status, bluf` — `409` if approving an `insufficient` one | `cop.assessment.status` |
| `POST` | `/incidents` | **`X-TOC-Role: battle_captain` required (Decision 3).** `location_id | threat_id | lat+lon+radius_km, title?, notes?` → roster = everyone in the area now **+ everyone assigned to the site** (site roll calls), all `unaccounted`; response carries `present/in_area/assigned` counts | `cop.incident.opened` |
| `POST` | `/incidents/{id}/request-checkins` | — → SMS to each unaccounted person + one chat broadcast naming them all, each carrying a per-person check-in link; stamps `checkin_requested_at`; response `{requested, deliveries, simulated}` | `cop.incident.checkins_requested` |
| `POST` | `/checkin/{token}` | **no auth** — the link from the message. `{note?, lat?, lon?}`; position defaults to where the wall has the person. Clears their roster row as `safe` via `app`. `404` bad token, `409` roll call closed | `cop.person.checkin` + `cop.incident.contact` |
| `PATCH` | `/incidents/{id}/roster/{person_id}` | `status (safe|contacted|unreachable|assist|injured|unaccounted), method, note` — one contact attempt | `cop.incident.contact` |
| `PATCH` | `/incidents/{id}/close` | `notes?` — records how many were never reached | `cop.incident.closed` |
| `POST` | `/intel/refresh` | runs live collectors (GDACS) and upserts by `external_id`; `502` if the source is unreachable — a broken source must not look like a quiet one | `cop.intel.refresh` / `refresh_failed` |
| `POST` | `/seed` | dev only — wipe and reload synthetic data | |

## 3.1 The watch (§3.1 of the PRD)
| Method | Path | Body | Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/watch` | | who has the floor, elapsed/remaining, next watch, overlap state; also on `/snapshot.watch` |
| `POST` | `/watch/take` | `battle_captain` — **role battle_captain** | first Battle Captain of a slot; `409` if held or a handover is pending |
| `PATCH` | `/watch/estimate/{S1|S2|S3|S6}` | `assessment, recommendation` — owners: S1 security/BC · S2 analyst/BC · S3 ea/security/BC · S6 BC | the running-estimate line; on `/snapshot.estimates`; ledger `cop.watch.estimate` |
| `GET` | `/watch/brief` | | the shift change brief: `significant_events` (bucketed), `current_status`, `next_shift`, `handover_items`, `acknowledgement.required_item_ids`; live until handover freezes it |
| `POST` | `/watch/handover` | `notes?, nstr` — **role battle_captain** | freezes the brief; watch → `pending_ack`; NSTR affirmed is logged as such |
| `POST` | `/watch/acknowledge` | `battle_captain, acknowledged_item_ids[]` — **role battle_captain** | `409` unless every `during_handover` item id is acknowledged; the watch transfers, both names on the ledger, the incoming BC holds the next slot from now |
| `PATCH` | `/watch/config` | `pattern: follow_the_sun|day_night, overlap_minutes?` — **role battle_captain** | |

## 4. The S2 drafter (`POST /assessments/draft`)
CLUE-style: the model drafts, code decides what it may say.
- **Code selects the evidence** — threats within radius (+5 km) of the subject, plus confirmed links.
- **Code computes `confidence`** from the evidence chain (independent sources, best source confidence, staleness). The model never grades its own confidence.
- **Code attaches the numeric band** to each estimative term. The model may only pick from the seven ICD 203 terms; anything else is replaced by the rubric.
- **Refuse-to-assess:** no evidence → `confidence: "insufficient"`, `refused: true`, `author: "rule:refuse-to-assess"`, and the row can never be approved (`409`).
- Model path (`claude-opus-5`, override `TOC_MODEL`) runs when `ANTHROPIC_API_KEY` is set or `TOC_DRAFTER=ai`; otherwise a deterministic heuristic drafts, so the wall works with no key.

## 5. Configuration
See `.env.example`: `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM`, `SLACK_WEBHOOK_URL`, `TOC_PUBLIC_URL` (where check-in links point — the wall serves `/checkin/<token>`), `TOC_SECRET` (signs tokens), `ANTHROPIC_API_KEY` / `TOC_DRAFTER`.

## 6. Client expectations
- Poll `/snapshot` every 30 s. Production: SSE on the same payload.
- Every list row is clickable and flies the map to the thing.
- `synthetic: true` threats render with a SYNTHETIC tag; `synthetic: false` with LIVE and the source.
- Show `source` (provenance) wherever a record is opened. If the wall can't say where a fact came from, it isn't a fact.
- Roll calls: `unaccounted` and `unreachable` sort first; VIPs first within a status. `tel:` links on phones.
