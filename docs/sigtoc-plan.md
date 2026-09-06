# Sigtoc — the plan for S2 as a working intelligence section

**Status:** plan, 2026-09-05. Written after the wall's hierarchy, overlays, and graphics were built (PRD v3.31). Nothing
in this document is built unless it says so. The PRD stays the authority; the sections here are drafted so they can be
lifted into PRD §5 as each phase lands.

**Scope:** this is a cross-module plan, not a request to bury all of Sigtoc inside Cop Talk. Sigtoc is a separate
module / sub-repo and remains the canonical home for intelligence objects and analyst workflow. Cop Talk gets the live
S2 slice that belongs on the common operating picture: red actors, sightings, report pins, threat graphics, warning
flags, and the effect of Intel on S3 movement. The two products meet through an explicit contract: Sigtoc owns and
works the intelligence picture; Cop Talk displays the tactical slice and can submit field reports back into it.

## 1. The honest state

Sigtoc today is a collection engine with products bolted on. What works: requirements that write themselves from the
wall, a collection plan against a real source catalog (six keyless live sources), threats as rings, assessments in
ICD 203 terms with a computed confidence, the area assessment in both its faces (what is reported, what the analyst
judges), the INTSUM as a diff, warnings the Battle Captain releases as FLASH, and a case graph built from SPOTREPs
with everything suggested until an analyst confirms it. Since today: every active requirement is a named area of
interest on the S2 overlay, threats fade with age and draw their links, and S2 can draw a TAI, an NAI, or an
observation post by hand.

What is missing is the other side. The wall tracks 2,400 of our own people to the person and has **no object for the
enemy**. It has no threat overlay in the doctrinal sense — no danger areas, no likely ambush sites, no kill zones, no
avenues of approach, no restricted terrain — and nothing that connects a threat overlay to what it means for a
movement on the S3 side. Reports from the field file into a case and never reach the map. Nothing counts sightings,
nothing draws a pattern, nothing turns "three sightings at dusk" into a proposal. The analyst reads; the analyst
cannot yet *work*.

The plan below fixes that in the order an S2 would: first the red force and the threat overlay, then the reporting
and collection cycle that feeds it, then the analysis that reads it, then the products that carry it, then the
sources that widen it. Implementation should preserve the product boundary: build the S2 domain once in Sigtoc, expose
the live subset to Cop Talk, and avoid a duplicate "mini-Sigtoc" inside the COP.

## 2. Module boundary and contract

Sigtoc and Cop Talk should share the same intelligence picture without becoming the same product.

| Surface | Responsibility | Must not become |
| :--- | :--- | :--- |
| **Sigtoc sub-repo** | Source of truth for actors, sightings, reports, threat graphics, NAIs, RFIs, collection, assessments, case links, warnings, INTSUMs, estimates, annexes, and analyst dispositions | A passive feed viewer that depends on Cop Talk to make or validate intelligence objects |
| **Cop Talk / wall** | Live map and staff surface: show the current red picture, show report pins and S2 graphics, flag S3 movement/site risks derived from Sigtoc, and let users submit SPOTREPs into Sigtoc | A second analyst workbench with its own actor dossiers, pattern analysis, collection board, or product generation |
| **Integration contract** | Stable APIs, shared schemas, or a shared package for the five core object types below, plus event updates for map changes and report disposition status | Ad hoc copying between repos or profile-specific objects that drift apart |

The ownership rule is simple: **Sigtoc owns the object; Cop Talk owns the live presentation.** A Cop Talk action can
create an input for Sigtoc, such as a SPOTREP from the wall or phone, but Sigtoc disposition decides whether that input
becomes a sighting, a threat graphic, an assessment, a case edge, or a dismissed report.

## 3. The model, in one picture

Everything Sigtoc adds is one of five things, and every one of them carries a source and a grade (Admiralty
reliability A–F, credibility 1–6), a time, and a place:

| Object | What it is | Where it shows |
| :--- | :--- | :--- |
| **Actor** | The other side as a thing with a name: an enemy unit with echelon and strength on a military desk; a threat actor — an individual, a group, an organization — with type and size on a corporate desk. Same object, profile-named, like ranks and the graphics catalog. Carries an order-of-battle card: composition, equipment, known TTPs, assessed intent, last known position | Owned in Sigtoc. Displayed as a red icon on Cop Talk and the S2 overlay at its last known position; worked in Sigtoc's *Who is out there* panel |
| **Sighting** | One observation of an actor: time, place, source (a report, a feed, a liaison), grade, what was seen. The chain of sightings is the track | Owned in Sigtoc. Displayed as breadcrumbs on Cop Talk/S2 when relevant; read by Sigtoc's time wheel and threshold rules |
| **Report** | A SPOTREP / SALUTE / SITREP from our own people, filed from a phone or the wall, with place and time. Exists today but only inside a case; becomes first-class on the map | Created from phones, Cop Talk, or Sigtoc. Shown as a pin until the Sigtoc analyst disposes of it: corroborate, link (to an actor, a threat, a case, an NAI), promote, or dismiss |
| **Threat graphic** | The threat overlay drawn by hand from the graphics catalog (§3.4), extended for S2: danger area, likely ambush site, engagement / kill zone, attack or IED hot spot, avenue of approach, mobility corridor, no-go and slow-go terrain, restricted area, obstacle or UXO, hostile checkpoint, hostile observation post, surveillance detection point. Each carries confidence and a valid window as well as the source | Owned in Sigtoc using the shared graphics contract. Displayed on Cop Talk's S2 layer and on S3 wherever a movement leg crosses one |
| **Decision point** | The event template's join: an NAI, the indicator watched there, the PIR it serves, and the decision it informs — "if X is seen at NAI 3 before 1800, the convoy takes ASR BLUE". Drawn as a graphic, tied to a requirement and to a graphic on S3 | Owned in Sigtoc. Displayed on Cop Talk when it changes the live plan; worked in Sigtoc's decision support matrix and brief |

The existing **requirement / NAI**, **threat**, **assessment**, **case**, **warning**, and **INTSUM** stay as they are and
gain edges to these: a sighting can promote to a threat, a threat can attach to an actor, a report can feed a case, an
NAI counts the sightings inside it, a warning rule can fire on a threshold.

## 4. Lines of effort

### LOE 1 — The threat picture: red force and the threat overlay

The S2 overlay gets its other half. Built first because everything after it needs these objects.

- **Actors** (`s2_actors`): id, profile-named type (unit / individual / group / organization), name and aliases,
  echelon or size, strength or headcount as an assessed range in words (not a score), equipment, TTPs as short lines,
  assessed intent, status (active / dormant / neutralized), the case it belongs to if any, owner, dates. A card on the
  panel and a red marker at the last known position. Sigtoc owns the card and edits; Cop Talk receives the live marker.
  On the COP the actor's marker is the enemy situation; in Sigtoc it carries its track.
- **Sightings** (`s2_sightings`): actor, time, place (lat/lon, place name, and the NAI it fell in, computed), source
  object (report / threat / feed item / liaison / analyst), grade, what was seen, confidence that it was this actor
  (confirmed / probable / possible). The last confirmed or probable sighting is the last known position. Sigtoc keeps
  the full track; Cop Talk shows the last known position and recent breadcrumbs. Sightings older than a configurable
  age draw faint; the track is the last N.
- **The threat graphic catalog** extends the graphics object (§3.4) with the S2 types above. Each S2 graphic gains
  `confidence` (confirmed / probable / possible / template) and `basis` (the reports or sightings behind it, or
  "doctrinal template"). A template is drawn from doctrine before anything is observed and says so; observation
  raises its confidence. The graphics contract must work across the Sigtoc repo and Cop Talk so both clients render the
  same object.
- **Effects on our own movement.** A derived check, not a drawn thing: every movement leg (§3.4) is tested against the
  threat graphics in its window. A leg that crosses a danger area, an ambush site, or a kill zone gets a flag on the
  S3 overlay and on the movement's card — "MSR TIGER crosses Danger Area 2 (probable, 2 reports)". This is the first
  place Intel changes what Ops sees without anyone writing a memo. Same check for a site inside a threat graphic.
- **Seed.** The brigade: an OPFOR reconnaissance element with three sightings around the FARP at dusk, a danger area
  at the bridge on MSR TIGER, a likely ambush site on the convoy's turn at the demonstration route, an avenue of
  approach into the FOB, a hostile OP on the ridge. The corporate desk: a surveillance actor seen twice at the SF HQ
  loading dock (the seeded case already tells this story), a hot spot around the DC-East operator's address, a
  surveillance detection point on the motorcade route.

*Decision needed:* whether the threat overlay is the graphics object extended (recommended: one draw tool, one
ledger, one render path on all three clients) or a separate object.

### LOE 2 — Reporting and collection: the cycle's input

- **SPOTREP from the phones.** A form on S1 (who saw it), S2 (what), and the COP tab: SALUTE fields — size, activity,
  location (the phone's position or a tap on the map), unit or description, time, equipment — plus free text and a
  photo later. Filed as a report with the reporter's identity and grade A2 into Sigtoc. Lands on Cop Talk's map inside
  seconds as a pin with a REPORT chip on the S2 rail badge.
- **Disposition in Sigtoc, visible on the wall.** The analyst opens a report and does one of four things: *corroborate* (raises
  credibility, marks it on the source), *link* to an actor as a sighting, to a threat, to a case, or to an NAI, *promote*
  to a threat (draws the ring), or *dismiss* with a reason. Every disposition on the ledger. Cop Talk updates the pin
  status but does not own the disposition workflow. Reports with no disposition after a configurable time show as a
  backlog count on the S2 headline.
- **RFI** as a tasking kind (§5.10a): any section asks S2 a question with a deadline; S2 owes it in its inbox; the
  answer is an assessment, a note, or "no information", on the ledger. The tasking machinery already exists.
- **Collection tasked from the map.** An NAI label gets TASK COLLECTION, which raises the collection tasking
  prefilled with the place, the window, and the PIR; the tasking cascade (§5.10a) opens the S3 operation. When the
  mission reports, the report links to the NAI and advances the PIR.
- **The ISR synchronization matrix** as a Sigtoc view, not a Cop Talk object: NAIs down the side, time across, and in each cell
  the source or asset watching (from the collection plan and from accepted collection taskings), with the gaps
  hatched. This is the collection manager's board; the data is already there.

### LOE 3 — Analysis: IPB and pattern

- **Pattern of life from the data.** A time wheel (day of week against hour of day) of sightings and reports, per actor
  and per NAI; an activity count per NAI over the last 7 / 30 days; a change-since-last-INTSUM line. All computed from
  sightings and reports; nothing is drawn that the data does not hold.
- **Thresholds as rules.** "N sightings of one actor within D days at one NAI", "a report inside a template graphic",
  "an actor's last known position inside a site's radius" propose a warning or an assessment draft the way the
  existing rule proposes a FLASH. Rules suggest; the Battle Captain releases. Thresholds are per deployment settings.
- **IPB as products the wall already half has.** *Define the environment*: the AO boundary graphic and an area of
  interest graphic. *Describe effects*: terrain and weather effects as S2 graphics (no-go, slow-go, restricted) plus the
  weather threats the feeds already bring and the sun times the wall already computes. *Evaluate the threat*: the order
  of battle from actors, their TTPs, and their doctrinal templates. *Determine COAs*: threat courses of action as named
  sets of S2 graphics (an avenue of approach, an objective, a timeline) with the analyst's likelihood in ICD 203 terms —
  most likely, most dangerous — each with the indicators that would confirm it.
- **The decision support matrix.** Decision points as objects (§2): NAI, indicator, PIR, decision, the S3 graphic or
  movement it changes, and who decides. On the panel as a matrix, on the map as a graphic, in the brief as the open
  decisions for the next watch.
- **The workbench (§5.11)** gains actors and sightings as node types; the link chart, timeline, and time wheel read them.

### LOE 4 — Products and dissemination

- **The intelligence estimate** as a document: the running-estimate line grows into the standard estimate — the
  situation, the threat (actors, capabilities, COAs), the effects, conclusions, and the collection plan — generated from
  the objects and edited by the analyst, versioned, on the ledger.
- **The intelligence annex** to an operation (§5.10a): when an operation opens on a subject, S2 can attach the annex
  generated from that subject's picture — the threat graphics that touch it, the actors near it, the COAs, the PIRs and
  NAIs, the collection tasked. Disseminated and acknowledged like every other product.
- **Graphic INTSUM.** The INTSUM diff gets a map panel: what moved on the red side since the last one.
- **The threat assessment per place** is the rated area assessment (§5.6), already built; it gains a link to the actors
  and threat graphics inside the place.

### LOE 5 — Sources beyond the feeds

- **Our own people as a source, graded.** Reports already carry A2; liaison reports (host-nation, local police,
  venue security) become a report kind with their own reliability, graded by the analyst over time.
- **Premium connectors** stay [LATER] and keyed: OSAC, Flashpoint, Dataminr, Recorded Future, ACLED live, OpenSanctions
  for entity checks against actors.
- **Imagery and full-motion video** are out of scope for this plan; a still image attached to a report is in LOE 2.

## 5. Sequencing

| Phase | Builds | Why in this order |
| :--- | :--- | :--- |
| **1** | Shared object contract; LOE 1 in full; LOE 2's SPOTREP intake from phones and Cop Talk, and Sigtoc disposition | The objects everything else reads. Ends with Sigtoc owning the red force, Cop Talk showing it on the map, S3 feeling the threat overlay, and reports flowing in from the field |
| **2** | LOE 2's RFI, collection from the map, the ISR sync view; LOE 3's pattern of life and thresholds | Closes the cycle: ask, collect, see, be warned. Sigtoc owns the workflow; Cop Talk shows actionable changes |
| **3** | LOE 3's IPB products, threat COAs, decision points and the DSM; LOE 4's annex and estimate | The staff products, which need everything above to be worth generating. These live in Sigtoc and publish only live effects back to Cop Talk |
| **4** | LOE 4's graphic INTSUM; LOE 5 | Widening, not deepening |

Phase 1 is roughly the size of the overlays work just finished. Phases 2 and 3 are each smaller than phase 1.

## 6. Rules that hold throughout

- Nothing is scored. Strength, likelihood, and confidence are words from the fixed lists, never numbers we made up.
- Every object carries its source and grade, and a rule only ever *suggests*; a human confirms, releases, or dismisses.
- A doctrinal template is drawn as a template and says so until observation raises it.
- Both profiles run the same objects; only the words differ (enemy unit / threat actor, ambush site / attack site,
  echelon / size).
- What Intel produces changes what Ops sees on its own overlay, by derivation, not by memo: a leg through a danger
  area is flagged where the leg is drawn.
- Do not duplicate Sigtoc in Cop Talk. Cop Talk can create reports and display the live layer; Sigtoc owns actor
  dossiers, dispositions, analysis, collection, products, and the durable intelligence ledger.

## 7. Open questions for the author

1. Confirm the integration shape between the Cop Talk repo and the Sigtoc sub-repo: shared package, API boundary, or
   generated schema client. Recommendation: stable schema/API first, shared rendering helpers only where they reduce
   duplication.
2. Threat overlay as the graphics object extended, or a separate object. Recommendation: extended.
3. "SR zones" in the author's note — if this means surface danger zones, those belong to S3's range graphic; if it
   means something else (a specific restricted-zone type), name it and it goes into the S2 catalog.
4. Whether phones file SPOTREPs in phase 1 (recommended) or the wall alone first.
5. The threshold defaults for the first rule: three sightings, seven days, one NAI is the proposal.
