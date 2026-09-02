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

**[TONIGHT] — placeholder.** A handful of synthetic threat markers near real locations, so the COP reads as blue *and* red. Each has a title, severity, radius, source, observed time, and a confidence. They're fake and labeled as such in the data.

**[NEXT] — the real thing.** The full S2 spec was written and is preserved in `docs/archive/PRD-v2-trust-safety.md` §4 and `docs/archive/PRD-v1-travel-risk.md` §6.5. What carries forward unchanged:

- **Three confidence axes** — source reliability (A–F), information credibility (1–6), analytic confidence (ICD 203) — always stated separately
- **Confidence is not probability** — estimative language from a fixed seven-term list with numeric bands
- **Refuse to assess** — no conclusion without evidence; the gap is published instead
- **Evidence traceability** — every judgment links to dated, graded source material

**How S2 gets built:** as an agent, not a platform. Anthropic's CLUE is the reference shape — Claude with tool access to the sources, doing collection and first-pass assessment, with the confidence discipline enforced in code around it. S2's output lands on the wall as threats on the map, assessments in the panel, and open PIRs that haven't been answered yet.

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
