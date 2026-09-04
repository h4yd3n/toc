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

### S6 — decisions L–N

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `POST` | `/cop/incidents/{id}/roster` | `person_id` **or** `name, phone?, role?`, `note?` — any role (Decision N) | adds a missed name with `basis: manual`; a visitor becomes a `source: manual` person on the site's team. Ledger `cop.incident.roster_added` |
| `POST` | `/cop/incidents/escalate` | | runs the 15-minute rule now (the app runs it every minute — Decision M): `unaccounted` with a check-in request older than 15 min, or opened 15 min ago with no attempt, → `unreachable`, `updated_by: rule:escalation-15m`. Ledger `cop.incident.escalated` |
| `POST` | `/cop/comms/sms/inbound` | Twilio form fields `From`, `Body` | Decision L. Matches the sender to a person by phone; first word SAFE/OK/YES → `safe`, HELP/SOS → `assist`, INJURED/HURT → `injured`, anything else → `contacted` with the text as the note. Replies TwiML. With `TWILIO_AUTH_TOKEN` set the `X-Twilio-Signature` must verify (403 otherwise); without it the endpoint is a simulator and the ledger says so |

Roster order (Decision M): unreachable, assist, injured, unaccounted, contacted, safe; VIPs first within a status.

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

## 3.2 Sigtoc — requirements and the collection plan (`/v1/s2`, PRD §5.2–5.3, §5.7)
Mounted in the COP app (the wall's S2 panel) **and** runnable standalone: `make run-s2` → `sigtoc.api:app` on :8002. Same DB.

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `GET` | `/s2/requirements?status=&kind=` | | every requirement with its `coverage {covered,total,pct,gaps}` |
| `GET` | `/s2/requirements/{id}` · `/plan` | | the synchronization matrix: indicator → live sources (with reliability, cadence) → covered, or `recommended` sources for the gap |
| `POST` | `/s2/requirements` | `place, lat, lon, window_from?, window_to?, purpose, priority, radius_km?` — roles battle_captain / security / analyst / ea (Decision H) | a directed requirement; ledger `s2.requirement.created` with coverage |
| `PATCH` | `/s2/requirements/{id}` | `status, priority, indicators[]` | the analyst adds or drops indicators; coverage recomputes |
| `POST` | `/s2/requirements/sync` | a wall snapshot | standing requirements upsert/expire — the COP calls this as a library after every S1/S3 write and at startup |
| `GET` | `/s2/coverage` | | the whole plan: fully-covered count, average coverage, gaps ranked by requirements affected with recommended sources |
| `GET` | `/s2/indicators` · `/s2/sources` | | the taxonomy and the catalog (`configured` = built and keyed; `enabled`, `cadence`, `reliability` are the operator's) |
| `PATCH` | `/s2/sources/{id}` | `enabled, cadence, reliability` — Decision K | ledger `s2.source.updated` |
| `GET` | `/s2/query?lat&lon&radius_km` | | the standalone use: threats held near a point and requirements whose subject is nearby |

Standing requirements write themselves: `req_loc_<site>`, `req_trip_<trip>`, `req_evt_<event>`; a trip's requirement expires when the trip is cancelled or its window passes. Directed places count as blue-force points for collection relevance. Every requirement carries a `country` (ISO) derived from the site, the destination, or the place name.

**Collection** — `POST /cop/intel/refresh?source=` runs every enabled and configured collector (or one), in the registry `sigtoc.collectors.registry`: GDACS, USGS, NWS (point events, kept when near a blue-force point or big enough to matter anywhere); WHO DON, State Dept, FCDO (country-scoped: matched to the countries our requirements are in and placed at our first requirement there, `scope=country`); ACLED and CLSTR when keyed. Each source's outcome is written to its `last_collected_at` / `last_result` and to the ledger as `cop.intel.refresh` or `cop.intel.refresh_failed`; one failure does not stop the rest. Response: `{sources: [{source, ok, collected, created, updated | error}], created, updated, collected, failed[], countries[]}`. `TOC_SOURCES_CONFIGURED` pins which sources count as live; `TOC_OFFLINE=1` makes none live (tests).

## 3.3 Sigtoc — organic reports and cases (`/v1/s2`, PRD §5.10 #1–2, §5.11)

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `POST` | `/s2/reports` | `text, kind (spot/sitrep/note), reported_by, reporter_role?, at?, lat?, lon?, place?, case_id?, credibility?` — roles security / ep / ea / analyst / battle_captain | a SPOTREP from our own people: `source: ops`, reliability A, credibility 2 by default. With `case_id`, extraction runs and the response carries `extracted {entities, relationships, events, evidence_added}`. Ledger `s2.report.filed` |
| `GET` | `/s2/reports?case_id=` | | reports, newest first |
| `GET` | `/s2/cases` | | only the cases the caller's role may read, with counts and `pending_review` |
| `POST` | `/s2/cases` | `title, kind (general/person/site/actor), subject_type?, subject_id?, summary?` — roles battle_captain / analyst (Decision Q) | ledger `s2.case.opened` with `on_person` |
| `GET` | `/s2/cases/{id}` | | the case, its graph (suggested + confirmed), its reports, and `analysis {links[], pattern}`. **Every read is on the ledger** (`s2.case.read`) |
| `GET` | `/s2/cases/{id}/queue` | | the review queue: every `suggested` entity, relationship (with names), and event, each with `evidence[] {report_id, quote, reliability, credibility}` |
| `POST` | `/s2/cases/{id}/decide` | `kind (entity/relationship/event), id, decision (confirm/reject), note?` — battle_captain / analyst | ledger `s2.case.confirmed` / `s2.case.rejected` |
| `POST` | `/s2/cases/{id}/entities/{eid}/merge` | `into` | the analyst says two entities are one; aliases kept, evidence and edges moved. Ledger `s2.case.merged` |
| `GET` | `/s2/cases/{id}/views?entity_id=&confirmed_only=` | | data for the three views: `link_chart {nodes, edges[grade, status, dashed]}`, `timeline[]`, `time_wheel {grid 7×24, peak, pattern}` |
| `PATCH` | `/s2/cases/{id}/close` | | ledger `s2.case.closed` |

Extraction (Decision P) only suggests. Without `ANTHROPIC_API_KEY` it is a cited heuristic: capitalized names and initials, `@handles`, phone numbers, emails, plates after "plate"/"reg", and an `associate` link when two people share a sentence with an association word. With the key, the model (`TOC_MODEL`, default `claude-opus-5`) returns the same shape with an exact quote per item; anything without a quote is dropped. Every item's evidence carries the report's grade, so a relationship's `grade` is the best reliability and credibility among its citations.

## 3.4 Sigtoc — Area Assessment (`/v1/s2/area-assessments`, PRD §5.6, Decision I)

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `POST` | `/s2/area-assessments` | `requirement_ids[1..6]` (directed only), `title?`, `purpose?` — battle_captain / analyst | drafts the comparison; ledger `s2.area.drafted` with per-candidate reported/quiet/gap counts and `approvable` |
| `GET` | `/s2/area-assessments` · `/{id}` | | list (with `places`) or the full product |
| `PATCH` | `/s2/area-assessments/{id}` | `status: draft/review/approved` — battle_captain / analyst | `409` on approve when `approvable` is false. Ledger `s2.area.status` |

Product shape: `indicators[]` (rows), `candidates[]` (columns) each with `cells[]` — `state` is `reported` (`likelihood` from the ICD 203 list, `band`, code-computed `confidence` with `confidence_basis`, `evidence[]`), `quiet` (a tasked source, nothing reported; `confidence: low`), `gap` (`recommended[]` sources), or — for the baseline row only — `facts` (`facts[]` public holidays in the window from Nager.Date; a failed lookup says so) — plus `counts`, `worst`, `bluf`, `author`. No score, rank, or composite field exists (Decision I). Evidence is the wall's threat table within the requirement's radius (+5 km buffer) observed between 90 days before the window and its end; a threat's `event_type` maps to an indicator, unmapped ones are listed as `unclassified`. `refusal` is set and approval is refused when no candidate has a reported or quiet cell.

## 3.5 Sigtoc — INTSUM (`/v1/s2/intsum`, PRD §5.6, Decision G)

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `POST` | `/s2/intsum/draft` | — battle_captain / analyst | drafts now, covering everything since the last INTSUM's `period.to` (24 h if none). Ledger `s2.intsum.drafted` |
| `GET` | `/s2/intsum` · `/latest` · `/{id}` | | headlines, or the full product |
| `POST` | `/s2/intsum/{id}/release` | `notes?` — **battle_captain only** | `409` if already released. Ledger `s2.intsum.released` |

The fixed-time draft: the COP app runs a ten-minute clock that drafts once per calendar day once `TOC_INTSUM_HOUR_UTC` (default 5) has passed — including at startup if the hour was missed. `TOC_INTSUM_CLOCK=off` disables it (tests). Product structure is fixed: `headline` (NSTR when nothing significant), `requirements` (active/standing/directed counts; created, expired, answered), `new_threats` (observed in the period, worst first, each attributed to the active requirements it falls inside, P1 first), `wall` (links, posture, roll calls), `reports` + `cases`, `products` (assessment and area-assessment events, pending area assessments), `collection` (live sources with last run, collector runs, gaps ranked by requirements affected).

## 3.6 Operations (`/v1/cop/operations`, PRD §5.10 #3) and dissemination (`/v1/s2/products`, §5.10 #4)

| Method | Path | Body / params | Notes |
| :--- | :--- | :--- | :--- |
| `POST` | `/cop/operations` | `subject_type (event/trip/location), subject_id, title?, from_assessment_id? \| from_area_id?, notes?, tasks?[]` — battle_captain | the cited product must be `approved` (409 otherwise); without `tasks` the standard skeleton for the subject kind is created. Ledger `cop.operation.opened` |
| `GET` | `/cop/operations` · `/{id}` | | with `tasks[]`, `resources[]`, `tasks_done/total`, `pct`, `blocked`, `resources_open` |
| `PATCH` | `/cop/operations/{id}` | `status (planned/active/complete/cancelled), notes?` — battle_captain | ledger `cop.operation.status`. Complete/cancelled operations leave the wall |
| `POST` / `PATCH` | `/cop/operations/{id}/tasks` · `/{task_id}` | `title, section (S1/S2/S3/S4/S6), owner?, due_at?` · `status (todo/doing/done/blocked), owner?, note?` — any role | ledger `cop.operation.task` on status change |
| `POST` / `PATCH` | `/cop/operations/{id}/resources` · `/{res_id}` | `item, qty, note?` · `status (requested/approved/issued/denied), note?` | the S4 ask and its answer; ledger `cop.operation.resource` |
| `POST` | `/s2/products/{ptype}/{pid}/disseminate` | `recipients[] (roles, person ids, names), channel (wall/chat), note?` — battle_captain / analyst | `ptype` is `assessment`, `area`, or `intsum`; the product must be approved / released (409). `chat` posts one line to Slack when configured, else `simulated`. Ledger `s2.product.disseminated` with `created_to_sent_min` |
| `POST` | `/s2/products/{ptype}/{pid}/ack` | — the caller's actor / role | acknowledges the caller's row (actor match first, then role); an unlisted reader is recorded as an unsolicited read. Ledger `s2.product.acknowledged` with `sent_to_ack_min` |
| `GET` | `/s2/products/{ptype}/{pid}/distribution` · `/s2/products/unacknowledged` | | recipients with latencies and `stale` (unread > 2 h); the INTSUM's products section carries `unacknowledged` |

The snapshot's `events[]` and `trips[]` carry `operation` (summary or null) and the snapshot has `operations[]` (planned and active).

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
