# TOC — Tactical Operations Center
## Product Requirements Document

**Version:** 3.1
**Date:** 2026-09-02
**Status:** Prototype running — web wall + native iOS against one API

> [!NOTE]
> **Scope tags:** **[TONIGHT]** is in the prototype being built now. **[NEXT]** is the following iteration. **[LATER]** is roadmap.

---

## 1. What This Is

**TOC is a corporate security operations center organized the way a military TOC is organized** — a staff structure (S1 personnel, S2 intelligence, S3 operations, S4 supply, S6 communications) arranged around a single common operating picture.

The center of the screen is a map. Around it, every staff section's status is visible at once, the way a TOC's wall is: personnel disposition, intelligence assessments and open questions, operations calendar, equipment posture. A Battle Captain reads the whole wall in a glance, and anything on the wall can be clicked to drive the map to it.

It runs as a web app now, and as native iOS and Android apps later, against one backend.

**The feel:** a strategy game's command view. Simple to read, immediate to interact with, comprehensive underneath. The map animates; the panels are live; nothing requires a manual.

---

## 2. The Staff Structure

This is the organizing principle for the whole product. Every feature belongs to a section.

| Section | Military function | Corporate translation | TOC module | Status |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | Personnel | Where everyone is, who's assigned where, who's on shift, how to reach them | **Blue Force Tracker** | **[BUILT]** |
| **S2** | Intelligence | External and open-source threat intel, assessments, PIRs | **Sigtoc** | **[BUILT]** live GDACS collection, analyst-confirmed links, CLUE-style drafter with refuse-to-assess |
| **S3** | Operations | Executive travel, corporate events, planned activity | **Ops Calendar** | **[BUILT]** travel + events (attendees generate trips), write API for EAs |
| **S4** | Supply / Logistics | Equipment, residence security, security team kit | **Equipment Board** | **[LATER]** |
| **S6** | Communications | Check-ins, accountability roll calls, incident comms | **Accountability** | **[BUILT]** check-in, roll call with call log; alerting **[LATER]** |

S1 and S3 feed each other: S3 says who is going where and when; S1 shows where they are now. S2 overlays threats on both. S4 says what they have with them.

---

## 3. The Common Operating Picture — The Wall **[TONIGHT]**

The COP is one screen. It never navigates away.

```
┌──────────────────────────────────────────────────────────────────────┐
│  POSTURE BAR   people · present · traveling · on shift · threats     │
├────────────┬────────────────────────────────────────┬────────────────┤
│            │                                        │                │
│  S1        │                                        │  S2            │
│  PERSONNEL │              THE MAP                   │  INTEL         │
│            │                                        │                │
│  locations │      blue: locations & people          │  threats       │
│  by count  │      red: threats                      │  assessments   │
│  travelers │      click anything → fly to it        │  open PIRs     │
│  on shift  │                                        │                │
│            │                                        │                │
├────────────┴────────────────────────────────────────┴────────────────┤
│  S3 OPERATIONS   ── timeline: active travel · upcoming events ──      │
└──────────────────────────────────────────────────────────────────────┘
```

**The map:**
- Global by default. Dark basemap. Smooth fly-to on every interaction.
- **Blue force:** locations (HQ, offices, data centers, residences, venues) as pins with a count badge. Travelers as distinct moving-person pins at their current location.
- **Red force:** threats as translucent radius circles, colored by severity.
- **Zoom behavior:** zoomed out, nearby locations cluster into one pin with an aggregate count. Zoomed in, each location stands alone. Click a location → side panel lists every team and every person assigned there, with on-shift status. That's the "zoom in far enough to see every person" behavior.

**The panels:**
- Every row in every panel is clickable and flies the map to that thing.
- Selecting anything on the map opens its detail in the nearest panel.
- Panels are compact — counts, status colors, short names. Detail lives one click deeper.

**Posture bar:** the numbers a Battle Captain wants at a glance. Total people, present at a location, traveling, security on shift, active threats. Overall posture color.

---

## 4. S1 — Personnel: Blue Force Tracker **[TONIGHT]**

**Locations.** HQ, offices, data centers, executive residences, event venues. Each has a position, a type, a posture (normal / elevated / critical), and a sensitivity tier. Residences are restricted-tier: they exist because the security team needs them, and they are never shown to a general audience.

**Teams.** Every team belongs to a location. Security teams are a special kind: they have shifts.

**People.** Every person belongs to a team, has a role, and may be flagged VIP. Their **current position** is derived, never typed:

- If they have an active trip → they're at the trip's destination
- Otherwise → they're at their team's location

**Security shift status.** For security teams, who is on shift right now, and in what role. The posture bar counts them.

**Aggregation.** Every location reports: people assigned, people present, security on shift, VIPs present. These roll up into clusters when zoomed out.

**[NEXT]:** real-time check-in (a person confirms where they are), last-known-position freshness, off-duty vs. unreachable states.

---

## 5. S2 — Intelligence: Sigtoc

> [!NOTE]
> Sigtoc is a **standalone module with its own API and its own screen, embedded in the wall as the S2 panel.**
> The wall is one consumer of Sigtoc's contract; nothing in Sigtoc depends on the wall. (Decision 3a.)

### 5.1 Two missions, one engine

| Mission | The question | Where the requirement comes from | Status |
| :--- | :--- | :--- | :--- |
| **Force protection** | What threatens *our* people, sites, and events, now and in the near term? | **The blue force picture.** Every site, trip, and event on the wall generates standing requirements automatically. | Partly **[BUILT]** — threats filtered against blue force, per-subject assessments, refuse-to-assess. Auto-generated requirements **[NEXT]**. |
| **Decision support** | What is the environment in a place we are *considering* — an offsite, a conference, a new office — for a given window? | **A person asks.** A directed requirement names a place, a window, and a purpose; the place need not be on the wall. | **[NEXT]** |

Same machinery, two triggers. Everything after the requirement — collection plan, sources, grading, drafting, refusal — is identical.

### 5.2 Requirements are first-class

A requirement is the unit of work. Nothing is collected and nothing is assessed without one.

| Field | Meaning |
| :--- | :--- |
| `kind` | `standing` (generated from the wall) or `directed` (a person asked) |
| `subject` | a wall entity (site, trip, event, person) **or** an ad-hoc place: name, coordinates, and a time window |
| `question` | the PIR in plain words — generated for standing requirements, written for directed ones |
| `purpose` | why it matters: "CEO board meeting", "candidate offsite venue" — drives which indicators weigh |
| `priority` | 1–3, human-set for directed; standing requirements inherit from the subject (VIP travel outranks a routine site) |
| `window` | when it matters; standing requirements track the subject's window, directed ones are explicit |
| `status` | `active` → `answered` → `expired`; a requirement with no decision or window is not a requirement |
| `owner` | who asked, or "S1/S3" when generated |

**Standing requirements write themselves.** A new trip on the wall creates one; a new event creates one per venue window; a site has one that never expires. When the trip ends, the requirement expires. The S2 analyst never types "is Riyadh safe for the CEO" — the S3 entry did that.

**Directed requirements are a form.** Place, window, purpose, priority. That is the whole input for the Lisbon question.

### 5.3 The collection plan — sources recommend themselves

The requirement determines the sources, not the other way around. Each requirement is decomposed into **indicators** — observable facts that would answer it — and each indicator maps to the sources that can observe it. That mapping is the synchronization matrix, and it is generated, not hand-built.

```
Requirement:  "Threats to the CEO's Riyadh visit, 1–4 Oct"
  ├── Indicator: hazardous weather / natural events in the window      → GDACS, NOAA        ✓ covered
  ├── Indicator: advisory level and change                             → State Dept RSS     ✓ covered
  ├── Indicator: civil unrest or political violence within 50 km       → ACLED, GDELT       ✗ no source connected
  ├── Indicator: health notices for the country                        → WHO DON            ✓ covered
  └── Indicator: targeted threat reporting against Western business    → commercial feed    ✗ not subscribed
Coverage: 3 of 5 indicators. Gaps are visible before anyone asks for an assessment.
```

Rules:
1. **Coverage is shown, always.** An indicator with no connected source is a collection gap on the plan — so refuse-to-assess (§5.5) is never a surprise.
2. **Sources are recommended by indicator**, from the catalog in §5.8. Connecting one is an admin action; recommending it is automatic.
3. **Cadence is per source, set by the analyst.** Defaults ship with each connector. **[NEEDS RULING]** the defaults — they should come from someone who has run collection, not be invented here.
4. **Relevance is filtered against blue force and against directed subjects.** The world's events are collected; only those touching a requirement's subject reach the wall.

### 5.4 Collection and processing **[BUILT for GDACS; pattern for all]**

Connector → normalize → deduplicate (`origin_key`, so one wire story republished forty times is one source) → grade → store with provenance (`source`, `observed_at`, `url`). A broken source fails loudly. Absence of evidence is not evidence of safety.

Every item carries the three confidence axes — source reliability (A–F, a property of the source, set by an analyst), information credibility (1–6, a property of the report), and, later, the analytic confidence of any judgment built on it (computed by code, never asserted by the model). Confidence is not probability; estimative terms come from the fixed ICD 203 list.

### 5.5 Analysis — the boundary **[BUILT]**

The machine collects, normalizes, filters, deduplicates, and **drafts**. A human grades sources, confirms threat links, and approves products. The drafter may only choose estimative terms from the fixed list; code attaches the band and computes confidence from the evidence chain. **When there is no qualifying evidence, the product is a collection gap, not a finding, and it cannot be approved.** This is what makes "as automated as possible" safe.

### 5.6 Products

| Product | Trigger | Answers | Status |
| :--- | :--- | :--- | :--- |
| **Threat** | collection | something happened near a subject — a ring on the map with source, severity, confidence | **[BUILT]** |
| **Assessment** | a wall subject | the finding for one trip, event, or site: BLUF, judgments with term + band + confidence, evidence, gaps | **[BUILT]** |
| **Area Assessment** | a directed requirement | the environment for a place and window that may not be on the wall; **several candidates compared side by side** | **[NEXT]** |
| **INTSUM** | daily, standing | what changed in the last 24 h across every active requirement: new threats, changed scores, expired windows, open gaps | **[NEXT]** |
| **Warning** | collection | an imminent, specific threat to a subject — FLASH to the floor | **[LATER]** with S6 alerting |

**The Area Assessment compares; it does not score.** Candidates are laid side by side on what is known, how well it is known, and what is missing — bands, confidence, and gaps per indicator. Ranking is the human's. **[NEEDS RULING]** whether to add a numeric composite; the recommendation is no — v1's scoring model was invented and could not be defended.

**The INTSUM is a diff**, not a report written from scratch: it is what the standing requirements produced since the last one. Fixed structure so a Battle Captain reads it at shift change in under five minutes. **[NEEDS RULING]** publication time and whether it is auto-published or reviewed first.

### 5.7 Surfaces (Decision 3a)

**Sigtoc API** — its own contract, versioned like the COP's:
- requirements: create directed, list, expire; standing ones appear as the wall changes
- plan: the collection matrix for a requirement, with coverage and gaps
- collect: run connectors for a requirement or for everything
- query: *"threats near <place> in <window>"*, *"what do we hold on <topic>"* — the standalone use
- products: assessments, area assessments, INTSUMs; draft / review / approve

**Sigtoc screen** — a small product UI: the requirements list with coverage bars, the query box, the products library. It is what an analyst lives in.

**The wall's S2 panel** embeds the same thing: threats, assessments, open requirements. One codebase, two surfaces.

### 5.8 Source catalog — recommended by indicator

| Indicator | Source | Access | Status |
| :--- | :--- | :--- | :--- |
| Natural hazards | GDACS | free, keyless | **[BUILT]** |
| Earthquakes | USGS | free, keyless | **[NEXT]** |
| Severe weather (US) | NWS / NOAA alerts | free, keyless | **[NEXT]** |
| Humanitarian / conflict situation | ReliefWeb API | free, keyless | **[NEXT]** |
| Civil unrest, political violence | ACLED · GDELT | free key · free | **[NEXT]** |
| Health notices | WHO Disease Outbreak News | free RSS | **[NEXT]** |
| Travel advisories | State Dept per-country RSS · FCDO | free | **[NEXT]** — the State Dept JSON endpoint is dead |
| Baseline for an unfamiliar place | Wikidata · Nager.Date holidays · NOAA climate normals | free | **[NEXT]** for Area Assessment |
| Sanctions, entities | OpenSanctions | free | **[LATER]** |
| Targeted threat reporting | OSAC · Flashpoint · Dataminr · Recorded Future | login / paid | **[LATER]** premium connectors |

An indicator with no connected source shows as a gap on every plan that needs it. That is the honest state, and it is the prompt to connect one.

### 5.9 Open decisions for §5

1. **INTSUM publication** — auto-published at a fixed time, or drafted for review and released by the Battle Captain?
2. **Who may create directed requirements** — analysts only, any security role, or anyone (an EA planning an offsite)?
3. **Numeric composite on the Area Assessment** — none (recommended), or a single band per candidate derived by a rule you can defend?
4. **Signal retention** — how long raw collected items are kept; the ledger is forever, but the feed is not.

---

## 6. S3 — Operations: Travel & Events

**[TONIGHT] — travel.** A trip has a traveler, an origin, a destination (a location or a raw coordinate), departure and return times, a purpose, and a status (planned / active / complete). An active trip moves the traveler's pin. The S3 timeline shows active and upcoming travel.

**[NEXT] — events.** A corporate event has a venue, a time window, and attendees. Two months out it's on the calendar so S2 can assess threats against it and S1 can plan security coverage. Attending VIPs each get a trip generated.

**[LATER]** — long-range planning view, security coverage assignment per event.

---

## 7. S4 — Supply: Equipment Board **[LATER]**

Who has what. Mostly laptops and phones at a tech company, but for the security team it's kit, and for executive residences it's cameras, access control, and — where lawful and policy allows — armed coverage.

Entity sketch: `Equipment` (type, serial, assigned to person or location, status). Not built tonight.

---

## 8. S6 — Communications: Accountability **[BUILT]**

The TOC's first job when something happens at a site is to reach every person who is supposed to be there.
That is a roll call, and it is the reason the S1 picture exists.

**Open a roll call** on a site, a threat, or a point. The roster is everyone whose *current* position is in the
area at that moment — present at the site, visiting it, or a traveler inside the threat's radius. Every name
starts **UNACCOUNTED** with their phone and email beside it.

**Work the roster.** Each contact attempt is one action — SAFE, NO ANSWER, NEEDS ASSIST, INJURED — and each is a
ledger entry with who called, when, how, and what was said. Unaccounted and unreachable names sort to the top;
VIPs first within a status. The posture bar shows the unaccounted count until it reaches zero.

**Close it** with notes. The record shows how many were reached and how many never were — that number is the
after-action report.

**Check-in** is the other direction: a person confirms where they are, which overrides their derived position for
12 hours (Decision 2). **[LATER]:** push a check-in request to a roster, alerting from S2 to the floor, shift handover notes.

---

## 9. Who Uses It

| User | What they do on the wall |
| :--- | :--- |
| **Battle Captain** | Reads the whole wall. Owns the shift. Escalates. |
| **Security team** | Sees their own posture, who's on shift, where the VIPs are |
| **Intelligence analyst** | Feeds S2. Reads S1/S3 to know what to assess against |
| **Chiefs of staff, EAs** | Populate S3 — travel, events — so the floor knows what's coming |
| **Incident response** | When something happens, pulls up the location and knows who's there and what they have |

The audience is security. The data entry is everyone who plans an executive's movement.

---

## 10. Tonight's Prototype — Exact Scope

**Built:**
- Backend: `/v1/cop/*` endpoints on the existing FastAPI app, SQLite via the existing SQLAlchemy layer, synthetic seed data
- Web app: React + Vite + TypeScript, MapLibre GL, the wall layout from §3
- S1: locations with clustering, teams and people in the detail panel, on-shift status, posture bar
- S3: active trips moving traveler pins, travel timeline
- S2: synthetic threat circles with detail cards
- An API contract document so the native apps can be built against the same endpoints

**Synthetic:** every person, location, trip, and threat. Residences are fake addresses. Nothing real goes in a public repo.

**Not tonight:** auth, roles, real-time updates, events, S4, S6, real intelligence, mobile apps.

---

## 11. Platform Plan

Matches the Washi pattern — a web app and two native apps against one backend.

| Platform | Stack | When |
| :--- | :--- | :--- |
| **Web** | React 19, Vite, TypeScript, MapLibre GL | **[TONIGHT]** |
| **Backend** | FastAPI, SQLAlchemy, SQLite → Postgres | **[TONIGHT]** |
| **iOS** | SwiftUI, MapKit, XcodeGen | **[NEXT]** |
| **Android** | Kotlin, Jetpack Compose, MapLibre Native | **[NEXT]** |

The native apps are native for a reason: the map has to be fluid and the animations have to be immediate, and that's what MapKit and Compose are for. The web app is built against the same `/v1/cop` contract, so the apps share the backend and the data model, not the UI code.

---

## 11.0 Priorities (2026-09-02)

1. **Coptoc** — the COP is the product and the thing the author can defend from experience.
2. **Sigtoc** — S2 exists to feed the wall; more collectors and a real drafter path come after the wall is solid.
3. **Modtoc** — last. ROOST (osprey: rules engine used by Discord/Bluesky/Matrix; coop: review console used by Notion) covers most of this ground. Modtoc stays as-is; evaluate adopting ROOST before investing further.

## 11.1 Repository Layout

| Folder | Module | Role |
| :--- | :--- | :--- |
| `coptoc/` | **Coptoc** | The COP — `api/` (S1/S3/S6), `web/` (the wall), `ios/` |
| `sigtoc/` | **Sigtoc** | S2 — collectors, the drafter, the intel→policy bridge |
| `modtoc/` | **Modtoc** | The content-moderation engine. **Not part of the COP** — a separate tool for a company that also runs a consumer platform, sharing the repo and the ledger |
| `shared/` | — | Models, database, the hash-chained ledger |

## 12. Data Model

**S1:**

| Entity | Key fields |
| :--- | :--- |
| `Location` | `id`, `name`, `type` (hq / office / datacenter / residence / venue), `lat`, `lon`, `city`, `country`, `posture`, `sensitivity` |
| `Team` | `id`, `name`, `location_id`, `function`, `is_security` |
| `Person` | `id`, `name`, `role`, `team_id`, `is_vip`, `on_shift`, `shift_role` |

**S3:**

| Entity | Key fields |
| :--- | :--- |
| `Trip` | `id`, `person_id`, `origin_location_id`, `dest_location_id` or `dest_lat`/`dest_lon`/`dest_name`, `depart_at`, `return_at`, `purpose`, `status` |
| `Event` **[NEXT]** | `id`, `name`, `venue_location_id`, `start_at`, `end_at`, `attendee_ids` |

**S2 (placeholder):**

| Entity | Key fields |
| :--- | :--- |
| `Threat` | `id`, `title`, `lat`, `lon`, `radius_km`, `severity`, `source`, `observed_at`, `confidence`, `synthetic` |

**Derived, never stored:** a person's current position; a location's counts.

---

## 13. Data Sources & Integrations

Every fact on the wall came from somewhere, and the wall says where. Each record carries a `source`
(provenance) and the model is one-directional: **source system → connector → COP tables → the wall.** The
COP never writes back to a source system.

| Section | Fact | Comes from | Status |
| :--- | :--- | :--- | :--- |
| S1 | People, teams, roles, VIP flag, phone, email | HRIS / directory (Workday, Okta, Google Directory) | seed tagged `hris:workday` — connector **[NEXT]** |
| S1 | Who is on shift | Security scheduling / guard-force system | manual on the wall — connector **[LATER]** |
| S1 | Where someone actually is | Badge system, check-in app, EP team | check-in **[BUILT]** — badge feed **[LATER]** |
| S3 | Executive travel | Travel management system (Concur, Egencia, Navan), executive calendars | seed tagged `travel_system:concur` / `calendar:google` — connector **[NEXT]** |
| S3 | Corporate events and attendees | Calendar, event platform, EA entry | write API **[BUILT]** — calendar connector **[NEXT]** |
| S2 | Natural hazards | GDACS (UN OCHA / EC JRC) — free, keyless | **[BUILT]** live |
| S2 | Earthquakes, severe weather | USGS earthquake feed, NWS/NOAA alerts, national met services | **[NEXT]** — same collector shape as GDACS |
| S2 | Country and city advisories | State Dept, FCDO, OSAC | **[NEXT]** |
| S2 | Civil unrest, crime, conflict events | ACLED, GDELT, news RSS | **[NEXT]** |
| S2 | Targeted threats, online chatter | Commercial intel (Flashpoint, Recorded Future, Dataminr) | **[LATER]** premium connectors |
| S6 | Contact channel | Phone/SMS (Twilio), Slack, mass-notification (Everbridge) | tel: links **[BUILT]** — outbound **[LATER]** |

**Connector rules** (from Sigtoc's collector contract):
1. A connector returns rows shaped for the COP table, keyed by `external_id`, and the API upserts — re-running is idempotent.
2. A broken source must fail loudly (`502`, ledger `refresh_failed`), never return an empty success. Absence of evidence is not evidence of safety.
3. Every row keeps `source`, `observed_at`, and a `url` back to the origin.
4. Relevance is filtered server-side against blue-force positions, so the wall shows what touches *our* people and sites, not the whole world.

---

## 14. Decisions Log

| # | Question | Decision (2026-09-02) | Enforced in |
| :-- | :--- | :--- | :--- |
| 1 | Residence visibility | Restricted layer, **off by default**; only a cleared viewer toggles it on | `GET /snapshot?restricted=` |
| 2 | What "present" means | **Hybrid** — derived position, overridden by a check-in within 12 h; older check-ins flagged stale | `service.CHECKIN_FRESH_HOURS` |
| 3 | Threat → site/person linkage | **Proximity suggests, analyst confirms**; only a confirmed link changes effective posture | `ThreatLinkRow`, `effective_posture` |
| A | Roll-call roster scope | **Everyone in the area now + everyone assigned to the site**, tagged by basis — 100% accountability of assigned personnel, the way you'd run it for an earthquake | `open_incident`, `AccountabilityRow.basis` |
| B | Check-in requests | **Push to the whole roster at once; work by exception.** A person's own check-in clears their row as SAFE via app; the floor calls only the non-responders | `request_checkins`, `checkin` |
| C | Restricted-layer clearance | **Battle Captain and Executive Protection only**, via `X-TOC-Role` | `service.RESTRICTED_ROLES` |
| D | Outbound channel for check-in requests | **SMS and chat at once.** Real when Twilio/Slack are configured; otherwise recorded and shown as SIMULATED — the wall never claims a message left the building when it didn't | `cop/comms.py` |
| E | Roll-call closure | **May close with names unaccounted**; the number is the after-action record | `close_incident` |
| F | Who opens a roll call | **Battle Captain only.** Anyone on the floor may work the roster | `ROLL_CALL_OPENERS` |

---

## 15. Open Decisions

1. **Inbound replies** — when someone replies "SAFE" to the SMS instead of tapping the link, should a Twilio inbound webhook clear them automatically (needs a public URL), or is the link enough for v1?
2. **Escalation timer** — after N minutes with no response, auto-flag unreachable and put the name at the top of the call list? What is N?
3. **Roster edits** — may the floor add a name the auto-roster missed (a visitor, a contractor), and does that need Battle Captain approval?

## Appendix — Version History

- **v1** — corporate travel-risk platform with a scoring model. Archived as `docs/archive/PRD-v1-travel-risk.md`. The scoring mathematics was invented and is not carried forward.
- **v2** — trust & safety decision support. Archived as `docs/archive/PRD-v2-trust-safety.md`. The evidence discipline is carried forward as the S2 spec.
- **v3** — the TOC as a staff-structured operations center with a common operating picture at its center.
- **v3.1** — S2/S3/S6 built; three decisions taken; data-sources map added; native iOS client.
- **v3.2** — roll-call scope, check-in requests, and restricted-layer roles decided and built (A/B/C).
- **v3.3** — S6 outbound (SMS + chat, real or simulated), check-in links, Battle-Captain-only opening (D/E/F).
