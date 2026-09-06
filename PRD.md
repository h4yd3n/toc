# TOC — Tactical Operations Center
## Product Requirements Document

**Version:** 3.31
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

### 1.1 Where this comes from — in the author's words

> The entire concept of this COP was born from my years of experience working in tactical operations centers that
> run twenty-four seven. Each TOC is also known as a fusion center, because it fuses S1, S2, S3, S4, S6, and other
> special sections — and they're all there, twenty-four seven. In Iraq I worked a whole year like this as the S2,
> hand in hand with Ops, the S3, to plan current and future operations. The importance of each role cannot be
> overstated.
>
> Intelligence and Ops are extremely important together, because Ops feeds Intel and Intel feeds Ops — but our
> sources are different. Ops feeds Intel with our soldiers on the ground, or other direct reports that come in
> through our soldiers or our pilots who see something from the air. Intel typically gets its reports from other
> sources: higher headquarters, or partner sources such as CIA, NSA, or partner nations. The S2 analyzes that
> information and tracks it over months, if not years — building cases, collecting evidence, building assessments.
>
> If the evidence was strong enough, there were times I would put together a target package and hand it to Ops to
> conduct an operation with boots on the ground. Ops would plan it directly with the combat units — arrange for the
> infantry to be at that location at that time — and figure out the logistics: helicopters, air operations, how to
> move soldiers where trucks can't go. Then we watched the operation on real-time feeds, with Intel constantly
> analyzing what came back from the soldiers and pushing information down to them if we got something from another
> source. That is the whole purpose of the TOC: to support ongoing operations.
>
> Here, the COP is the fusion cell. Sigtoc is the S2 function — the people monitoring threats twenty-four seven and
> pushing anything relevant down to the COP and to Ops, while also watching the COP. The S2's job is more specific:
> making sure intelligence assessments reach the right people at the right time, and that the information is timely
> and accurate. Modtoc, the moderation module, comes later — it's queue work, and ROOST has largely built that
> already, so there's no reason to reinvent it; being open source, we may take some of theirs and adapt it.

---

## 2. The Staff Structure

This is the organizing principle for the whole product. Every feature belongs to a section.

| Section | Military function | Corporate translation | TOC module | Status |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | Personnel | Where everyone is, who's assigned where, who's on shift, how to reach them | **Blue Force Tracker** | **[BUILT]** |
| **S2** | Intelligence | External and open-source threat intel, assessments, PIRs | **Sigtoc** | **[BUILT]** live GDACS collection, analyst-confirmed links, CLUE-style drafter with refuse-to-assess |
| **S3** | Operations | Executive travel, corporate events, planned activity | **Ops Calendar** | **[BUILT]** travel + events (attendees generate trips), write API for EAs |
| **S4** | Logistics | Supply, equipment, transportation | **Logistics Board** | **[BUILT]** supplies and equipment by site against a required level; inbound shipments; by exception |
| **S6** | Signal | Communications, networks, systems, accountability | **Signal Board** | **[BUILT]** systems by site with PACE comms; roll calls and check-ins (§8) |

S1 and S3 feed each other: S3 says who is going where and when; S1 shows where they are now. S2 overlays threats on both. S4 says what they have with them.

---

## 3. The Common Operating Picture — The Wall **[BUILT]**

The COP is one screen. It never navigates away.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ◇ TOC  DEFCON 3  DUBLIN WATCH · R. Kovac · 5h left   97 5 4 7 3  BC ▾ │
│ FLASH  Online threats against data center operators — DC-East   ACK  │
├──┬────────────────────────────────────────────────────────────────┬──┤
│S1│                                                                │S2│
│  │                         THE MAP                                │  │
│  │      blue: sites by posture, travelers, events                 │  │
│  │      amber/red rings: threats by severity                      │  │
│  │      a rail button slides its panel out over the map           │  │
│  │      clicking the map puts it away                             │  │
├──┴────────────────────────────────────────────────────────────────┴──┤
│  S3 OPERATIONS  events · trips (OP, COVER)     │  LOG  battle log    │
└──────────────────────────────────────────────────────────────────────┘
```

**The layout (decided 2026-09-04, replacing the three-column wall).** The map has the width. S1 and S2 live on
rails at the left and right edges and slide out over the map on demand — an open roll call lights S6 on the left
rail, pending warnings badge S2 on the right. They cover the map only: the S3 strip and the battle log run the full
width beneath and are never covered. A released Warning is a red FLASH row under the header. Every list shows every
row (a top-three cap was tried and rejected).

**The map:**
- Global by default. Dark basemap. Smooth fly-to on every interaction.
- **Blue force:** locations (HQ, offices, data centers, residences, venues) as pins with a count badge. Travelers as distinct moving-person pins at their current location.
- **Red force:** threats as translucent radius circles, colored by severity.
- **Zoom behavior:** zoomed out, nearby locations cluster into one pin with an aggregate count. Zoomed in, each location stands alone. Click a location → its card lists every team and every person assigned there, with on-shift status. That's the "zoom in far enough to see every person" behavior.

**The panels:**
- Every row in every panel is clickable and flies the map to that thing.
- Selecting anything on the map opens its card over the map.
- Panels are compact — counts, status colors, short names. Detail lives one click deeper.
- **Rail badges (v3.29).** A closed rail still tells the story: each rail button carries one count — red for an exception (unaccounted names, warnings awaiting release, red supply lines or late shipments, systems down), amber for work the section owes, dim for the plain count otherwise.
- **The strips under the header (v3.29).** A context row: where the board is cut (the declared AO or the home ground) and BMNT · sunrise · sunset · EENT computed from it, with DAY / TWILIGHT / NIGHT — arithmetic on the AO, never a feed. The FLASH row. And an open roll call, which takes the wall: a bar across the top with the count, the elapsed clock, the outstanding names as chips, and the one action that matters. At DEFCON 1, or with a critical warning released, the chrome goes red and the primary actions grow.
- **⌘K (v3.29).** One field that finds anything on the picture — a name among 2,400, a site, an event, a threat, a tasking, or one of the wall's own actions — and opens it where it lives.
- **DISPLAY toggles**, per browser or device: *lean labels* (drop panel hints, empty running-estimate lines, second lines) and *posture header* (posture first, five counters; FLASH, unaccounted, unreachable only when non-zero). Both default on.

**Posture reads as DEFCON.** Five levels — normal, guarded, elevated, high, critical — shown as **DEFCON 5 → 1**.
The wall's level is the worst site's effective level. The header chip reads "DEFCON X"; clicking it opens the list
of every level, lowest to highest, the current one highlighted with the number of sites at each. The confirmation
rule (Decision 3) forces 5, 3, or 1 from confirmed links; a Battle Captain may set 4 or 2 by hand from a site's card.
The level meanings shown are the US military DEFCON definitions, as the example the author chose; the words are one
table on the API. Counters beside it: personnel, traveling, VIP out, threats, confirmed.

---

### 3.0 The map-first sections **[BUILT]** (2026-09-05)

The author's direction: the picture is the product, and a section that is only a list is a spreadsheet inside the app. So every section is a *layer on the map* first and a *list you can dismiss* second. Each site carries its S4 and S6 health (the worst supply line or inbound shipment there; the worst system there and the PACE net in use), so S4 and S6 are layers that color the sites — red at FARP Eagle on fuel, amber at the brigade TOC on HF — with a badge that counts what is short or down; clusters wear the worst of their sites. A site with nothing tracked wears no badge, not a green one. On the wall the S4 and S6 layers are toggles beside the others, they switch on when their panel opens, and the panel filters to the selected site. On the phones every section tab is the map with that section's layer — S1 sites and travelers, S2 threats, S3 events and routes, S4 and S6 site health — and the section's list on a sheet with three rests: peek, half, full. Pull the sheet down to see the picture and up to read; a tap on its header cycles the three rests. (On Android the sheet owns the pointer from touch down, or the map view underneath takes the gesture; the emulator's synthetic swipes never moved it, a real finger does.)

### 3.1 The watch — shifts, running estimates, and handover **[BUILT]**

The wall has a Battle Captain but, until now, no concept of a *watch*. A TOC runs twenty-four seven and one human
cannot; the floor changes hands, and the moment it changes hands is where information is lost. This section is the
fix, and the battle log already holds most of the raw material.

**The shift model.** Configurable per deployment; the default is follow-the-sun in three eight-hour watches —
Singapore, Dublin, San Francisco — with a 12-hour day/night pattern as the alternative (Decision S). The wall always
shows the watch: *"Dublin watch · Battle Captain R. Kovač · 3h12 into shift · handover to San Francisco in 4h48."*
Shift boundaries are in the watch site's local time.

**The panels are running estimates.** Each staff section keeps a continuously current picture of its own area —
facts, what changed, assessment, gaps, recommendation. On the wall those pictures *are* the panels, and each has an
owner:

| Panel | Running estimate | Owner |
| :--- | :--- | :--- |
| S1 (left) | Personnel status and disposition | the floor / security |
| S2 (right) | Threat picture, assessments, open PIRs | the S2 analyst |
| S3 (bottom) | Travel, events, operations | ops, EAs |
| S6 (roll calls) | Accountability and comms | the Battle Captain |

What each estimate lacks today is its **assessment line**: a short, human-owned "S2 assesses…" / "S1 assesses coverage
is thin at DC-East tonight" kept current at the top of the panel, with a recommendation when there is one. Those four
lines are the spine of the handover.

**The shift change brief** is not a report written at handover. It is the running estimates read out at handover,
generated from the wall for the watch window, in the order it is briefed:

1. **Significant events this shift** — posture changes, threats confirmed, roll calls opened or closed and where they stand, trips started or ended, anything gone stale
2. **Current status** — the four assessment lines; posture; open incidents and unaccounted names; travelers in their windows; assessments in review; open PIRs
3. **Next shift** — events starting, trips departing or returning, requirements expiring, known collection gaps
4. **Handover items** — outstanding actions, and the outgoing Battle Captain's own "things to be aware of," in their words
5. **Acknowledgement** — the incoming Battle Captain accepts; both names go on the ledger

**Handover mechanics (Decision T).** The brief is generated; the outgoing Battle Captain annotates it; the incoming
Battle Captain acknowledges it. **The watch does not transfer until it is acknowledged.** Both names and the time
are on the ledger — the handover is itself a logged event.

**The overlap (Decision U).** Thirty minutes. The brief covers watch start → handover. Anything that arrives inside the
overlap is flagged *during handover*: it belongs to the incoming shift, and the incoming Battle Captain must acknowledge
each item explicitly, so nothing falls between two people.

**NSTR is a state (Decision V).** "Nothing significant to report" is a valid brief — and it must be *affirmed* by the
outgoing Battle Captain. An empty brief and an affirmed nothing are different things; the ledger shows which it was.

**Relationship to the INTSUM.** The INTSUM (§5.6) is S2's daily product across all standing requirements. The shift
change brief is the Battle Captain's product across all sections, once per watch. The S2 assessment line in the brief
is drawn from the same picture the INTSUM summarizes.

### 3.2 The hierarchy of a panel **[BUILT]** (2026-09-05, Decision W)

The wall read as a terminal not because it is dark but because everything on it was a monospace row with a fraction in it. The fix is a hierarchy, applied to every panel the same way, with the dark monospace wall kept as it is:

1. **One headline first.** Each panel opens with the number the Battle Captain asks for before any other — S1 *at post*, S2 *collection coverage*, S4 *lines at or above required*, S6 *systems up* — drawn large, with a bar. The S3 strip carries its own inline: events, how many are covered, trips active, the next thing.
2. **The exceptions as tiles.** Under the headline, small counted tiles; a tile for an exception (unaccounted, unreachable, to release, late, down) is drawn only when it is non-zero. S2 shows its threats as four counted blocks by severity.
3. **Ratios are bars.** Present over assigned per unit and per site, coverage per requirement, on hand over required. A bar reads from across the room; a fraction does not. The thresholds are the same everywhere.
4. **Cards for what happens, rows for what is counted.** Taskings, warnings, shipments, and rated places are cards with a title line, one line of context, and their actions. Rosters, sites, units, and threats stay rows.
5. **Sections are headed by the question they answer.** *How ready are we, by unit. Where we are. Who is moving. What is threatening us. What we have warned, or should. What we are asking. What we assess. What we know about places. What we still need to know. What is below the line. What is on its way. How to reach each site. What is down or degraded.* Proper-case sans for the question, monospace for the data line.
6. **Color carries meaning only.** Green, amber, and red for state; blue for our own things; nothing else colored.

Travelers group by destination, because the question is where our people are, not the alphabet.

### 3.3 The strip through NOW **[BUILT]** (2026-09-05)

The S3 strip is one time axis with NOW in it. The left quarter is *this watch so far*: every event on the ledger since the watch began, drawn as ticks in the colors the brief buckets them in, hour by hour, the summary on hover and the subject on click. The right is the horizon, compressed: the next 48 hours get a quarter of the width, the rest of the 90 days the remainder, so today is by hour and next month by week. Spans that began before now cross the line. The handover brief's first section, *significant events this shift*, is this left half read out; the snapshot carries it as `watch_log`.

### 3.4 The section overlays **[BUILT]** (2026-09-05, Decision Z)

An overlay is a section's own situation laid over the base map, the way acetate goes on a map board: the section's things forward, everything else still there, dimmed to a third. The S4 layer already worked because it repainted the sites with the section's state; S2 and S3 added their objects to the base without changing it, and their objects were thin. Now:

- **The chooser.** A row on the map — COP · S1 · S2 · S3 · S4 · S6. COP is everything. Opening a section's panel puts its overlay up; closing it returns to the COP. On the phones each section tab is its overlay.
- **S2 draws what an S2 owns.** Every active requirement is a *named area of interest*: a ring at its place and radius, numbered by priority, colored by how well it is collected (green, amber, red), labeled with its subject and coverage, marked when a PIR rides on it. Threat rings fade with age (full at observation, a quarter at thirty days); a threat with a confirmed link draws solid with a line to the site or person, a suggested one dashed. A site wears the analyst's rating (§5.6) instead of its headcount. A time window — 12 h, 3 d, 30 d, all — filters the threats, so a pattern shows. Nothing here needs data the wall does not have; the NAIs are derived from the requirements (`snapshot.nais`).
- **S3 draws movement, leg by leg.** A flight is an arc, a ground leg runs on the ground, lodging is a stop; the current leg is bold; a planned one dashed. Everything that moves is a *movement* (`snapshot.movements`): a serial, a delegation, one named person, or a shipment. The head of every group carries the unit or the event and the count; a shipment carries its ETA, red when late. An event wears its coverage and its operation's progress, red-ringed when coverage has a gap. The strip drives the map: hover a moment and what is not happening then dims; click to pin it.
- **Movement ownership.** S3 draws all movement, shipments included; S4 keeps stock and what is inbound, drawn as the dashed line to the site with the ETA and an inbound chip on the site marker. Same object, styled by the section looking at it.
- **The grouping rule (Decision Z).** A movement is one or more travelers on a shared route in a shared window, drawn as one line with a count. On a military desk the *unit* is the actor: trips group by battalion, origin, destination, and a six-hour window into a serial named for the unit — "1 ATK · 6 pax · Campbell → FARP Eagle". On a corporate desk the *individual* is the actor: nobody moves as a company, so trips group only by a shared destination event into a delegation — "Global Sales Kickoff · 8 travelers → Las Vegas" — and everyone else moves alone under their own name. A VIP never folds into a group. A group needs at least three travelers. The mode follows the legs: a flight makes it air.
- **The graphics object (v3.31).** Control measures the wall cannot derive — an MSR, an air corridor, a boundary, a range hot window, an access control point, a TAI, a retrans site, a supply point, a cordon — are drawn by hand. One object: a point, a line, or a polygon; a type from a catalog that sets its color, glyph, and owning section (S2: TAI, NAI, OP; S3: MSR, ASR, corridor, boundary, phase line, ACP, checkpoint, LZ, assembly area, range, cordon; S4: supply point, CCP, maintenance point; S6: retrans, coverage, CP); a name; an optional window; a note; what it is for. The catalog speaks doctrine on a military desk and plain words on a corporate one. Drawing needs edit on the owning section or the Battle Captain: pick the type under DRAW on the overlay chooser, click the points, double-click to finish, name it. Retired, not deleted. On the ledger, in the brief as operations, on all three clients under the overlay rules — the phones read them, the wall draws them. `/v1/cop/graphics`, `snapshot.graphics`, `coptoc/graphics.py`. The brigade's seed board carries MSR TIGER, air corridor GREEN, the range hot in the gunnery window, ACP 4, TAI 1 at the demonstration gate, RRT 1, the FARP's supply point, the FOB's CCP, and the brigade AO; the corporate desk carries the motorcade route, the board-dinner cordon, a rally point, a watch on the DC-East dock, and a medical point.

## 4. S1 — Personnel: Blue Force Tracker **[TONIGHT]**

**[BUILT] — names and ranks (2026-09-05).** A person carries last name, first name, middle initial, a rank abbreviation ("SSG", "CW3", "CPT"), and a pay grade — E1–E9, W1–W5, O1–O10, plus CIV and CTR — because the grade is the cross-service constant and services spell the same grade differently. Display follows the profile, the author's call: a military desk reads **LAST, First M. · SSG** — last name first so a roster sorts the way a roster does, the rank after the name; a corporate desk reads First Last. Both sort by last name. Map labels read "SSG Reyes" on a military desk and "Jordan" on a corporate one. Uploads accept a rank or a grade (E-6, e6, SSG all land as SSG / E6) and other services' abbreviations map to the same grade.

**[BUILT] — the task organization (2026-09-04).** A team can have a parent, an echelon (brigade / battalion / company), a short designation ("B/1", "3 AHB"), and an equipment line ("AH-64E ×8"). The S1 panel and the S1 tab lead with the task organization: brigade → battalions → companies, each with present/assigned, how many are away, and a red count for anyone unreachable or under a confirmed threat. Battalions fold and unfold; a company selects its site on the map. A flat set of teams (no parents) shows no tree and the team lists stand as before.

**The sample force is a Combat Aviation Brigade.** The author's decision (2026-09-04): one dataset, organized the way a heavy CAB is, not a corporate/military fork — a commercial deployment hides the sections it does not run (§11.2). HHC and five battalions, each with a headquarters company and four line companies: two attack reconnaissance battalions (AH-64E), an assault helicopter battalion (UH-60M), a general support aviation battalion (CH-47F heavy lift, command aviation, air ambulance), and an aviation support battalion (distribution, aviation intermediate maintenance, network support, ground maintenance). Roughly 2,400 people; the ASB together with every battalion's D company (aviation unit maintenance) is well over half of them — the author's experience of where a CAB's headcount sits. Headcounts and tail counts are approximate to a generic table of organization, not any real unit's; every name is invented. Home station is Campbell Army Airfield; the deployed sites are an exercise area (FOB Warrior, FARP Eagle, a range complex). Site types gained `airfield`, `cp`, `fob`, `farp`, `range`. The original executive-protection sample is kept as `dataset=corporate` for the test suite and as a second shape of the same model.

**[LATER]** unit positions from GPS telemetry (JBC-P / vehicle trackers) so companies move on the map the way travelers do; equipment readiness by bumper number.

**Locations.** HQ, offices, data centers, executive residences, event venues. Each has a position, a type, a posture (five levels, read as DEFCON 5 → 1; see §3), and a sensitivity tier. Residences are restricted-tier: they exist because the security team needs them, and they are never shown to a general audience.

**Teams.** Every team belongs to a location. Security teams are a special kind: they have shifts.

**People.** Every person belongs to a team, has a role, and may be flagged VIP. Their **current position** is derived, never typed:

- If they have an active trip → they're at the trip's destination
- Otherwise → they're at their team's location

**Security shift status.** For security teams, who is on shift right now, and in what role. The posture bar counts them.

**Aggregation.** Every location reports: people assigned, people present, security on shift, VIPs present. These roll up into clusters when zoomed out.

**[BUILT]:** real-time check-in and last-known-position freshness (12 h window, Decision 2); availability as a state of its own — on shift, off duty, available, unreachable (a roll call that could not reach you, or a stale check-in on the road).

---

## 5. S2 — Intelligence: Sigtoc

> [!NOTE]
> Sigtoc is a **standalone module with its own API and its own screen, embedded in the wall as the S2 panel.**
> The wall is one consumer of Sigtoc's contract; nothing in Sigtoc depends on the wall. (Decision 3a.)

### 5.1 Two missions, one engine

| Mission | The question | Where the requirement comes from | Status |
| :--- | :--- | :--- | :--- |
| **Force protection** | What threatens *our* people, sites, and events, now and in the near term? | **The blue force picture.** Every site, trip, and event on the wall generates standing requirements automatically. | **[BUILT]** — standing requirements write themselves from S1/S3 and expire with their subject; the collection plan shows coverage and gaps per requirement. |
| **Decision support** | What is the environment in a place we are *considering* — an offsite, a conference, a new office — for a given window? | **A person asks.** A directed requirement names a place, a window, and a purpose; the place need not be on the wall. | Requirement + plan **[BUILT]**; the Area Assessment product **[BUILT]** — candidates side by side, three cell states, no composite |

Same machinery, two triggers. Everything after the requirement — collection plan, sources, grading, drafting, refusal — is identical.

### 5.2 Requirements are first-class **[BUILT]**

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

### 5.3 The collection plan — sources recommend themselves **[BUILT]** (six keyless live sources, two more with keys; the plan shows the gaps)

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
3. **Cadence is per source and adjustable by whoever runs the system** — the analyst or an admin — from the source's settings, with every option available (manual, hourly, every few hours, daily, weekly). Each connector ships with a default that is a starting point, not a rule; the operator changes it as they learn the source. (Decision K.)
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
| **Area Assessment** | a directed requirement | the environment for a place and window that may not be on the wall; **several candidates compared side by side** | **[BUILT]** — `/v1/s2/area-assessments`; the S2 panel picks directed requirements and opens the matrix |
| **INTSUM** | daily, standing | what changed since the last one across every active requirement: new threats attributed to requirements, wall changes, organic reports and cases, products, collection and gaps | **[BUILT]** — drafts itself at `TOC_INTSUM_HOUR_UTC` (default 0500Z), the Battle Captain releases; NSTR when nothing happened |
| **Warning** | collection | an imminent, specific threat to a subject — FLASH to the floor | **[BUILT]** — suggested by rule (critical inside a radius, or elevated with a confirmed link), released only by the Battle Captain; SMS to the people at the subject, a post to the ops channel, an acknowledgement row per role; on the wall and both phones as a FLASH strip; expires after 24 h; on the INTSUM |

**The Area Assessment compares; it does not score** (Decision I). Candidates are laid side by side on what is known, how well it is known, and what is missing. Each cell is one of three states: **reported** — a term from the fixed list, its band, a code-computed confidence, and the evidence; **quiet** — a tasked source is watching and has reported nothing, which is worth exactly as much as that source's reliability and is never a finding of safety; **gap** — nobody is watching, with the sources that could. Reporting up to 90 days before the window counts as describing the place. A product where nothing is known for any candidate refuses and cannot be approved (§5.5). Ranking is the human's.

**The rated area assessment (v3.29, Decision X)** is the other half of the same product. Collection says what has been *reported* about a place; the analyst's rating says what S2 *judges* about it — against a fixed indicator list, green / amber / red per indicator, each with one line that says why, owned and dated. Still no composite: the picture is the row of ratings and the worst of them, and the reader ranks. The indicator list is configuration like the section titles — a brigade asks *routes, MEDEVAC reach, PACE, sustainment, ISR, host-nation, weather*; a corporate desk asks *transit corridors, trauma proximity, cyber redundancy, law-enforcement liaison* — set by the profile or `TOC_AREA_INDICATORS`. A place is a site on the wall or anywhere with a name; a new assessment supersedes the last, which stays as history on the ledger. Every site, trip, and event carries the strip for its place; the S2 panel lists every rated place worst first and compares any two side by side (`/v1/cop/areas`). The seed rates FARP Eagle, FOB Warrior, and Peason Ridge for the brigade, and Lisbon, Porto, and London for the corporate desk, in words that agree with what the S4 and S6 boards show.

**The INTSUM is a diff**, not a report written from scratch: it is what the standing requirements produced since the last one. Fixed structure so a Battle Captain reads it at shift change in under five minutes. Drafted at a fixed time and released by the Battle Captain (Decision G).

### 5.7 Surfaces (Decision 3a) **[BUILT]** — `/v1/s2` API mounted in the wall and standalone (`make run-s2`); the S2 panel shows requirements, coverage, gaps, the directed form, and the source settings

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

Domains held for deployment: **coptoc.com**, **sigtoc.com**, **modtoc.com** — one per module, matching Decision 3a's standalone-plus-embedded shape.
| Earthquakes | USGS | free, keyless | **[BUILT]** live — M6+ anywhere, anything within 400 km of a blue-force point |
| Severe weather (US) | NWS / NOAA alerts | free, keyless | **[BUILT]** live — polygon alerts within 150 km; zone-only alerts resolved through the zone endpoint, cached, at most 25 lookups per run |
| Humanitarian / conflict situation | ReliefWeb API | free, needs an approved `appname` | **[LATER]** — v1 is decommissioned and v2 refuses unregistered app names |
| Civil unrest, political violence | ACLED · GDELT | free key + email · free | ACLED **[BUILT]**, live when `ACLED_API_KEY` + `ACLED_EMAIL` are set (parser follows the documented shape; untested live). GDELT **[LATER]** — the GEO API is gone and the DOC API is rate-limited and has no coordinates |
| Clustered news events by country, with timelines | CLSTR (clstr.news) — a new, single-maintainer service; multi-source clusters and "situations", ~30–90 min behind the wires by design | free key, 100 req/day, 7-day history | **[BUILT]** trial, live when `CLSTR_API_KEY` is set; country-scoped; source reliability **F** until it earns a grade; its significance score is theirs, never ours |
| Health notices | WHO Disease Outbreak News | free JSON (the RSS is gone) | **[BUILT]** live — country-scoped |
| Travel advisories | State Dept RSS · FCDO Atom | free | **[BUILT]** live — country-scoped; level 3–4 / advise-against draw a ring at our site in that country, lower levels a marker only |
| Baseline for an unfamiliar place | Nager.Date holidays · Wikidata nearest settlement (NOAA climate **[LATER]**) | free, keyless | **[BUILT]** — public holidays in the window and the nearest settlement's name, population, and country appear as a `facts` cell on the Area Assessment |
| Sanctions, entities | OpenSanctions | free | **[LATER]** |
| Targeted threat reporting | OSAC · Flashpoint · Dataminr · Recorded Future | login / paid | **[LATER]** premium connectors |

An indicator with no connected source shows as a gap on every plan that needs it. That is the honest state, and it is the prompt to connect one.

### 5.10 Ops and Intel feed each other — what that adds to the requirements

§1.1 describes a loop the document had only half of. Intel's sources are external; **Ops' sources are our own people.**
Intel builds cases over time; when the evidence is strong enough the product goes to Ops, who plan and resource the
response; the floor watches it happen and Intel pushes anything new down to the people in the field. Four things
follow from that, none of which the wall has yet.

| # | Requirement | Military analog | Corporate form | Section | Status |
| :-- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Organic reporting is a first-class source.** Our own people report what they see, and S2 treats it as reporting from the most reliable source there is. | SPOTREP / SITREP from the unit | A security officer in the SF lobby reports a crowd forming; an EP agent reports the route is blocked; a traveler's check-in note. Each is a `Report` with who, where, when, what — and it is a Sigtoc source (`source: ops`, reliability graded like any other, typically A). | S3 → S2 | **[BUILT]** — `Report` (SPOTREP / SITREP / note) filed from the wall by security, EP, EA, analyst, or Battle Captain; `source: ops`, reliability A, credibility 2 until corroborated; filed into a case it runs extraction |
| 2 | **Cases that live for months.** S2 tracks a thing over time, accumulating evidence, with assessments that version rather than replace. | The target folder | A recurring protest group at HQ; a persistent online threat actor naming the company; a fixation case against an executive. A `Case` holds evidence and every assessment ever made on it. Threats are events; a case is the thread through them. | S2 | **[BUILT]** — `Case` (general / person / site / actor) holding reports, the graph, and the review queue; person cases need the Battle Captain or S2; every read on the ledger |
| 3 | **A product hands off to an operation.** When an assessment is strong enough, Ops plans the response and resources it. | Target package → OPORD | An approved assessment on the Vegas keynote becomes an `Operation`: tasks (advance the venue, vet transport, brief the principal), assignments (EP team, local vendor), and resource asks (S4: vehicles, kit). The wall shows the operation's status against the event. | S2 → S3 (S4 for resources) | **[BUILT]** — `Operation` opened by the Battle Captain from an *approved* assessment or area assessment (a draft is refused) or directly on a subject; starts with the standard task skeleton by staff section; S4 asks are requested by S3 and answered by S4; the event or trip card shows OP done/total |
| 4 | **Dissemination is tracked.** "Right people, right time" is a measurable: who a product went to, when, and whether they acknowledged it. | Distribution list and read-back | Every product carries recipients and acknowledgements; latency from `observed_at` → published → acknowledged is on the record. A warning nobody read is a failure the ledger should show. | S2 → S6 | **[BUILT]** — approved or released products are disseminated to roles or people (wall, or chat when Slack is configured); each recipient's acknowledgement and the latencies created → sent → acknowledged are on the ledger; unread past two hours is on the INTSUM as a failure |

The loop, closed: **Ops reports → S2 grades and files into cases → S2 assesses → the product is disseminated and
acknowledged → Ops plans the operation → the floor watches it → Ops reports.** The wall is where all of it is visible
at once, which is what a fusion cell is.

### 5.10a Taskings — work moving between sections **[BUILT]** (2026-09-05)

The object that carries a request from one staff section to another: S2 asks S3 for a collection asset over an area (a drone over the FARP during the rotation); S3 asks S6 to confirm PACE for an operation; S3 asks S4 for fuel at a site; S3 asks S1 for gate security at a ceremony. A tasking has who asked and who owes, what it is for (an operation, event, requirement, site, or trip), the asset or capability wanted, a window, a priority, and a status — requested → accepted → scheduled → complete, or declined with a reason. Raising one needs edit on the section it comes from; answering needs edit on the section it goes to; the Battle Captain can do either. A tasking whose window has opened and is not complete is late, and reads red. Every step is on the ledger; the handover brief carries what is open per section. Each section's panel on the wall, and each section's tab on the phones, shows what that section owes (with ACCEPT / SCHEDULE / COMPLETE / DECLINE), what it is waiting on, and a RAISE form. **Taskings create things when accepted (v3.29, Decision Y).** The tasking is the ask; the thing the owing section makes to answer it lives on that section's board. Accepting a *collection* tasking on a site, event, or trip opens an S3 operation with a collection skeleton (assign the asset, confirm the window and airspace, brief the requirement, fly and report to S2). Accepting a *supply* tasking books a planned shipment on the S4 board, categorised from the ask, due at the window. Accepting a *comms* or *coverage* (or movement / other) tasking whose subject already has an operation adds a task to it, owned by the answering section; with no operation it stays a plain ask. Each is linked both ways: completing the tasking closes what it made; the shipment arriving, the task done, or the operation closed completes the tasking with the result on it. Both objects log the link. The tasking card shows what it made as a chip that opens it.

### 5.10b Sigtoc as a working section — the plan

The S2 overlay has requirements and threats and nothing for the other side. The cross-module plan for the red force, the threat overlay (danger areas, ambush sites, kill zones, avenues of approach), field reporting from the phones, pattern analysis, thresholds, IPB products, and the decision support matrix is in `docs/sigtoc-plan.md` (2026-09-05), sequenced in four phases. Sigtoc remains the canonical intelligence module / sub-repo; Cop Talk shows the live S2 slice on the common operating picture and submits field reports back into Sigtoc. Phase 1 is the shared object contract, actors, sightings, threat graphics, S3 movement risk flags, and SPOTREPs that land on the map. **[PLANNED]**

### 5.11 The analyst's workbench — one graph, three views

The `Case` from §5.10 is the folder. This is what an analyst does inside it: link analysis, pattern of life, and
time-event charts — the products an S2 used to draw by hand, drawn by the system from the case's own evidence.
The product category is Palantir Gotham / i2 Analyst's Notebook; the wedge here is narrower on purpose.

**The model.** A case is a graph, and every element of it carries a source.

| Element | Fields | Notes |
| :--- | :--- | :--- |
| `Entity` | `id`, `type` (person · organization · account · phone · vehicle · place · device), `name`, `aliases[]`, `attributes{}` | Aliases resolve across sources — forty handles, one actor |
| `Relationship` | `from`, `to`, `type` (member_of · associate · contacted · funded · located_at · owns · …), `first_seen`, `last_seen`, `status` (suggested · confirmed · rejected), `evidence[]` | A dated, typed, sourced line between two entities |
| `Event` | `at`, `place`, `participants[]`, `type`, `summary`, `evidence[]` | What happened, when, where, who was there |
| `Evidence` | `signal_id` or `report_id`, `quote`, `source`, `reliability` (A–F), `credibility` (1–6) | The join that makes the chart honest — every edge and every event traces to a line in a report |

**The views are renderings, not products.** Because the model is one graph, all three are automatic:

| View | What it shows | Military name |
| :--- | :--- | :--- |
| **Link chart** | entities and relationships; force-directed; confirmed edges solid, suggested edges dashed; **source grade visible on every edge** — a confirmed A1 and a suggested D4 never look alike | association matrix / network diagram |
| **Timeline** | events on a time axis, filterable by entity; the case's own history | time-event chart |
| **Time wheel** | activity by hour-of-day × day-of-week per entity, from event timestamps | pattern-of-life analysis |

Plus the map: every `place` entity and located event already has a home on the wall.

**The boundary (Decision P).** The machine **extracts**: it reads reports and signals into entities, relationships, and
events, each cited to the line it came from, and proposes alias merges. Everything it produces is `suggested` until an
analyst confirms it. It never asserts a link without a citation, never grades a source, and never draws a line the
analyst can't trace back. This is the same rule as threat links on the wall (Decision 3), and it is what keeps a
link chart from filling with plausible lines nobody can defend.

**Access (Decision Q).** This is the tool that gets misused. Opening a case on a **person** requires the Battle Captain
or the S2 lead. Viewing a case is role-gated. **Every read of a case is written to the ledger**, not only every write —
the record of who looked at whom is part of the product.

**Build order (Decision O).** The graph model is designed now, because it changes how `Report` and `Case` (§5.10)
store evidence — they must be graph-shaped from the start. The views come after requirements, the collection plan,
and the Area Assessment. All three views ship together (Decision R): they are one model, and building one without the
others would mean building the model three times.

**The analysis is not deferred — only the pictures are.** Extraction into the graph *is* link, event, and
pattern-of-life analysis: once reports are read into entities, relationships, and events with times, the AI can state
"activity clusters Thursday nights" or "three accounts share infrastructure" as judgments in an assessment, with
evidence, before any chart exists. The views are how a human sees what the graph already holds. Two limits on
"automatic": there is nothing to link until sources report on *people* (organic reports, social monitoring, cases —
hazard feeds have no network), and automatic extraction makes automatic errors, which is why every extracted line is
suggested until confirmed.

**Not in scope.** Ingesting a platform's full event firehose; bulk data fusion; anything that competes with Gotham on
volume. Cases are case-sized. The value is provenance on every line, not scale.

**Status:** **[BUILT]** model with `Report`/`Case`, entities / relationships / events with evidence on every line, suggest→confirm review queue, analyst-decided alias merges, and the data for all three views (`/cases/{id}/views`: link chart nodes and edges with grade and status, timeline, 7×24 time wheel with the pattern stated as a sentence). Extraction is a cited heuristic (names, handles, plates, phones, emails, association in one sentence) with the model path behind `ANTHROPIC_API_KEY`. **[NEXT]** the pictures themselves; extraction from collected signals, not only reports.

### 5.9 Decisions for §5 (2026-09-02)

All taken — see §14 (G–J, and O–R for the workbench): INTSUM drafted at a fixed time and released by the Battle Captain; any security role or EA may create a directed requirement; no numeric composite on the Area Assessment; raw signals kept 90 days, cited signals as long as the product, the ledger forever.

---

## 6. S3 — Operations: Travel & Events

**[TONIGHT] — travel.** A trip has a traveler, an origin, a destination (a location or a raw coordinate), departure and return times, a purpose, and a status (planned / active / complete). An active trip moves the traveler's pin. The S3 timeline shows active and upcoming travel.

**[BUILT] — events.** A corporate event has a venue, a time window, and attendees. Two months out it's on the calendar so S2 can assess threats against it and S1 can plan security coverage. Attending VIPs each get a trip generated.

**[BUILT]** — long-range planning view (the next 90 days by week: events with coverage and gaps, trips, who is committed) and security coverage per event: a default rule (one lead, one agent per VIP, one more past twenty attending) the Battle Captain can override; only security-team people can cover; overlapping assignments are flagged on the ledger.

**[BUILT] — the itinerary (2026-09-04).** A trip may carry *legs*: flights, ground moves, and lodging, each with a place, a start and end, a label (carrier and number, property, provider), and a confirmation reference. Legs are optional on every business trip, VIP or not: present when the travel system or an EA supplied them, blank otherwise, never inferred. What they buy: the traveler's derived position follows the current leg (a flight in progress is placed at its arrival airport, a night at the hotel; between legs, where the last one ended), so proximity rules and roll calls see the hotel, not the city centroid; the person's detail shows the itinerary as a timeline with the current leg marked; the S3 agenda row shows the current leg. Sources: a travel-system CSV of legs (`/import/legs`, upsert by confirmation reference within a trip) and a pasted confirmation (`/import/itinerary`, one leg per line, places as IATA codes from a known table or `@lat,lon`; anything the parser cannot place is reported, never guessed — the §5.5 discipline applied to S3). EAs add and remove single legs by API. **[LATER]** booking-platform connectors (Concur, Navan) and airline status feeds.

---

## 7. S4 — Logistics: Supply & Equipment Board **[BUILT]**

Reinstated 2026-09-04 with §8 as the *background sections*, built for a generic operations center — military, government, police — where S4 and S6 are inside the TOC by doctrine. A commercial security desk hides them (§11.2).

**The doctrine.** S1, S2, and S3 are what the Battle Captain lives in. S4 and S6 are managed by someone on the staff and speak only when something is wrong: a shipment the force is waiting on is late, fuel at a site is below the line, a system the TOC depends on is down. So they roll up to one status each — GREEN nothing to say, AMBER watch it, RED it is a problem now — and the wall shows only that roll-up (a dot on the rail button) until someone opens the panel. The exceptions ride into the handover brief (§3.1) and the INTSUM.

**What S4 tracks.** *Supply lines*: a category (fuel, water, rations, medical, ammunition, parts, equipment, other), an item, what is on hand against what is required, at a site or force-wide. Below required is AMBER, below half of it RED. *Shipments*: what is inbound, from where, to which site, with an ETA, a status (planned / in transit / delayed / arrived / cancelled), and a priority; late or delayed is AMBER, an urgent one RED. Arrivals leave the board after a day. Owners: `battle_captain` and `logistics`. Everything is on the ledger (`cop.s4.*`), and S4 keeps a running estimate like every other section.

**[LATER]** vehicle and equipment readiness by bumper number (FMC / PMC / NMC), fuel consumption against days of supply, and unit tracking from GPS telemetry on the COP (§4) — the pieces a military or police deployment adds first.

---

## 8. S6 — Communications: Accountability **[BUILT]**

**[BUILT] — the signal board (2026-09-04).** Alongside accountability, S6 tracks the systems the TOC depends on: comms nets by PACE role (primary / alternate / contingency / emergency) per site, networks, applications, power, sensors, each up / degraded / down with a clock since the last change and a note. A primary net or power down is RED; anything else down or degraded is AMBER. The panel shows PACE per site — the best working net, so the Battle Captain knows how to reach each site *right now* — then the exceptions, then open roll calls. Owners: `battle_captain` and `signal`. Ledger: `cop.s6.system`.

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
12 hours (Decision 2). Check-in requests go out over SMS and chat at once (Decision 1) and a text back of SAFE, HELP, or INJURED works the roster by phone number (Decision L). Fifteen minutes with no response flags a name UNREACHABLE by rule and floats it to the top (Decision M). Anyone on the floor may add a missed name (Decision N). Shift handover notes live in the watch (§3.1). **[LATER]:** alerting from S2 to the floor (Warning product).

---

## 9. Who Uses It

**[BUILT] — users and permissions (2026-09-05).** One app; what you see and what you can change follows your permissions. A user has, per staff section, *edit*, *view*, or nothing, plus two flags: *battle captain* (the floor: watch, roll calls, FLASH release, DEFCON, operations) and *admin* (the directory). Presets name the common shapes — a supply sergeant is S4 edit with S1 and S3 view — and the grid is the truth. Tabs and rails you cannot view do not appear; panels you can view but not edit show no controls; the API enforces it, not just the UI. Sign-in for the prototype is picking a *profile* from a list — and the profiles are the roles themselves (Battle Captain, S1 Personnel, S2 Intelligence, S3 Operations, S4 Logistics, S6 Signal, Admin; on a corporate desk Executive Protection, Security, S2 Analyst, Executive Assistant), not invented people — the author's call, so the MVP has no fake roster to maintain and a real login later maps each person onto the same grid: the client sends `X-TOC-User`, and the server derives the role and the actor the rest of the API already checks, so the ledger names the person. Requests without a user keep working on the role header alone. The admin's grid lives under SETTINGS on the wall; the phones sign in from their SETTINGS menu. The sample directories: for the brigade, a Battle Captain, a knowledge manager (admin), the brigade S1/S3/S4, a battalion S2, a supply sergeant, a signal NCO; for the corporate desk, the equivalents. **[LATER]** a real login in front of it (README, "Before you deploy").

**Header counters open their section.** On the wall and the phones, PERSONNEL and the S1 counters open S1, THREATS / CONFIRMED / FLASH open S2, TRAVELING / VIP OUT / EVENTS go to S3.

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
| **iOS** | SwiftUI, MapKit, XcodeGen | **[BUILT]** — `coptoc/ios`, the wall with watch chip, estimates, roll call; S2 panels **[NEXT]** |
| **Android** | Kotlin, Jetpack Compose, MapLibre Native | **[BUILT]** — `coptoc/android`, the wall with S1/S2/S3/S6 panels, detail sheets, and every role-gated action; built and run on the Pixel 7 emulator |

The native apps are native for a reason: the map has to be fluid and the animations have to be immediate, and that's what MapKit and Compose are for. The web app is built against the same `/v1/cop` contract, so the apps share the backend and the data model, not the UI code.

---

## 11.0 Priorities (2026-09-02)

1. **Coptoc** — the COP is the product and the thing the author can defend from experience.
2. **Sigtoc** — S2 exists to feed the wall; more collectors and a real drafter path come after the wall is solid.
3. **Modtoc** — last. ROOST (osprey: rules engine used by Discord/Bluesky/Matrix; coop: review console used by Notion) covers most of this ground. Modtoc stays as-is; evaluate adopting ROOST before investing further.

## 11.2 The profile and the section set are configuration

**The profile (2026-09-05).** A menu beside the role menu on the wall — Battle Captain only — switches the deployment's shape and reloads the sample data. *Military*: S1–S6 by their staff codes, and the Combat Aviation Brigade (§4). *Corporate*: the product as it was before S4 and S6 — S1–S3 by the same names, the flat team list, and the executive-protection sample. The choice is the `TOC_PROFILE` setting (§11.3); the phones read it from the snapshot and show four tabs or six. Same model, same code, two shapes — the author's decision after first trying one dataset for both.

`TOC_SECTIONS` narrows the list further and `TOC_SECTION_TITLES=S4=SUPPLY,S6=COMMS` renames; S1–S3 cannot be switched off, and a corporate profile never shows S4 or S6 whatever the list says.

## 11.3 Settings — keys and options entered from the wall **[BUILT]**

Connecting a data source or a channel is a key, and keys used to live only in the server's environment. Now the wall has a **SETTINGS** button (Battle Captain only) with four groups: *source keys* (ACLED, CLSTR), *comms* (Twilio, Slack, the public URL), *the S2 drafter* (Anthropic key, model), and *staff sections* (§11.2), followed by the SOURCES list (enable, grade, cadence — Decision K). Rules: the environment always wins over the store, so a deployment that sets keys the 12-factor way is unaffected; stored values are encrypted at rest with `TOC_SECRET` and are **write-only** — the API reports set / not set, who and when, the last four characters of a secret, never the value; the ledger records that a key was set, never what it was. Keyless feeds need nothing. **[LATER]** an admin role distinct from the Battle Captain, and per-user permissions once there is an identity layer (README, "Before you deploy").

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
| `Location` | `id`, `name`, `type` (hq / office / datacenter / residence / venue), `lat`, `lon`, `city`, `country`, `posture` (normal / guarded / elevated / high / critical), `sensitivity` |
| `Team` | `id`, `name`, `location_id`, `function`, `is_security`, `parent_id`, `echelon` (brigade / battalion / company / team), `short`, `equipment` |
| `Person` | `id`, `name`, `role`, `team_id`, `is_vip`, `on_shift`, `shift_role` |

**S4 / S6:**

| Entity | Key fields |
| :--- | :--- |
| `SupplyLine` | `id`, `location_id` (null = force-wide), `category`, `item`, `on_hand`, `required`, `unit`, `note`; derived `status` (green / amber / red) |
| `Shipment` | `id`, `description`, `category`, `quantity`, `from_name`, `to_location_id`, `eta`, `status`, `priority`, `carrier`, `ref`; derived `health` |
| `System` | `id`, `name`, `category` (comms / network / application / power / sensor), `location_id` (null = enterprise), `pace`, `status` (up / degraded / down), `since`, `note`; derived `health` |

**S3:**

| Entity | Key fields |
| :--- | :--- |
| `Trip` | `id`, `person_id`, `origin_location_id`, `dest_location_id` or `dest_lat`/`dest_lon`/`dest_name`, `depart_at`, `return_at`, `purpose`, `status` |
| `TripLeg` **[BUILT]** | `id`, `trip_id`, `kind` (flight / ground / lodging), `label`, `ref`, `from_name`/`from_lat`/`from_lon` (not for lodging), `to_name`/`to_lat`/`to_lon`, `start_at`, `end_at`, `note`, `source`; derived `status` (done / current / planned) |
| `Event` **[BUILT]** | `id`, `name`, `venue_location_id`, `start_at`, `end_at`, `attendee_ids` |

**S2 (placeholder):**

| Entity | Key fields |
| :--- | :--- |
| `Threat` | `id`, `title`, `lat`, `lon`, `radius_km`, `severity`, `source`, `observed_at`, `confidence`, `synthetic` |

**Derived, never stored:** a person's current position; a location's counts.

---

## 13. Data Sources & Integrations

**[BUILT] — the spreadsheet upload (2026-09-05).** Every section takes what its people actually keep: an Excel workbook or a CSV, formatted however it was formatted — the author's requirement, because units keep Excel and keep it inconsistently. The flow is preview → mapping → commit. The app reads the workbook (values, not formulas), finds the header row under whatever title rows sit above it, proposes what each column means — the S2 drafter's model when a key is set, header matching otherwise — and shows a sample with what it cannot place. Nothing lands until a person presses COMMIT; rows that cannot be placed are reported, never guessed. S1 takes a roster (rank, name, a unit path like `B/1-101 ARB` that the importer splits into battalion and company, building the task organization as it goes; new companies hang under existing battalions, new battalions under the brigade). S3 takes a schedule (events, operations, travel; a place must be a known site or carry coordinates; a traveler must be in the directory). S4 takes a LOGSTAT (site or unit, class of supply, item, on hand, authorized) or a shipment list. S6 takes a comms status (site, system, PACE role, status). Upload needs edit on the section. Wall only — a spreadsheet is not a phone task. **[LATER]** the tasking object between sections (S3 schedules a collection asset against S2's plan; S6 confirms comms for an operation).

Every fact on the wall came from somewhere, and the wall says where. Each record carries a `source`
(provenance) and the model is one-directional: **source system → connector → COP tables → the wall.** The
COP never writes back to a source system.

| Section | Fact | Comes from | Status |
| :--- | :--- | :--- | :--- |
| S1 | People, teams, roles, VIP flag, phone, email | HRIS / directory (Workday, Okta, Google Directory) | **[BUILT]** as an export adapter: CSV import upserts by id then email, provenance `hris:csv`; OAuth connectors **[LATER]** (need accounts) |
| S1 | Who is on shift | Security scheduling / guard-force system | **[BUILT]** as a CSV import (`scheduling:csv`); a live connector **[LATER]** |
| S1 | Where someone actually is | Badge system, check-in app, EP team | check-in **[BUILT]**; badge feed **[BUILT]** as a JSON event stream (`POST /v1/cop/import/badge/events`: a badge-in is a check-in at the site) |
| S3 | Executive travel | Travel management system (Concur, Egencia, Navan), executive calendars | **[BUILT]** as a CSV import upserting by booking reference (`travel_system:csv`); API connectors **[LATER]** |
| S3 | Corporate events and attendees | Calendar, event platform, EA entry | write API **[BUILT]**; calendar **[BUILT]** as an ICS import (attendees matched by email, venue by site name or GEO, trips generated); Google/Outlook OAuth **[LATER]** |
| S2 | Natural hazards | GDACS (UN OCHA / EC JRC) — free, keyless | **[BUILT]** live |
| S2 | Earthquakes, severe weather | USGS earthquake feed, NWS/NOAA alerts, national met services | USGS + NWS **[BUILT]** live |
| S2 | Country and city advisories | State Dept, FCDO, OSAC | State Dept + FCDO **[BUILT]** live, country-scoped; OSAC **[LATER]** (login) |
| S2 | Civil unrest, crime, conflict events | ACLED, GDELT, news RSS | ACLED **[BUILT]** (key); CLSTR **[BUILT]** (key); GDELT **[LATER]** |
| S2 | Targeted threats, online chatter | Commercial intel (Flashpoint, Recorded Future, Dataminr) | **[LATER]** premium connectors |
| S6 | Contact channel | Phone/SMS (Twilio), Slack, mass-notification (Everbridge) | tel: links, outbound SMS + Slack, inbound SMS **[BUILT]** (simulated without credentials) — Everbridge **[LATER]** |

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
| G | INTSUM publication | **Drafted at a fixed time, released by the Battle Captain** — one human gate on the product the whole floor reads | §5.6 — enforced: a ten-minute clock drafts once per day at the fixed hour (and at startup if missed); only `battle_captain` may release |
| H | Who creates directed requirements | **Any security role, plus EAs**; the S2 analyst owns the answer | §5.2 — not yet built |
| I | Area Assessment scoring | **No numeric composite.** Bands, confidence, and gaps per indicator; the human ranks | §5.6 — enforced: the product has no score field; three cell states |
| J | Raw signal retention | **90 days**; anything cited by a product lives as long as the product; the ledger is forever | §5.4 — not yet built |
| K | Collection cadence | **Per source, operator-adjustable**, all options exposed; shipped defaults are starting points, not rules | §5.3 — not yet built |
| L | Inbound SMS replies | **The check-in link is enough for v1**; a Twilio inbound webhook (a "SAFE" text clears the row) comes with a public deploy | §8 — built: `POST /v1/cop/comms/sms/inbound` (SAFE / HELP / INJURED by phone; Twilio-signed when configured, a simulator otherwise) |
| M | Escalation timer | **15 minutes** with no response → auto-flag UNREACHABLE and float the name to the top of the call list | §8 — enforced: a one-minute clock runs `escalate_due`; flagged rows carry `rule:escalation-15m`; unreachable and needs-assist sort first |
| N | Roster edits | **Anyone on the floor may add a missed name** (visitor, contractor); tagged `basis: manual` and logged | §8 — built: `POST /v1/cop/incidents/{id}/roster`; a visitor becomes a `manual` person on the site's team |
| O | Workbench build order | **Design the case graph now** (it shapes `Report`/`Case`); build the views after requirements, collection plan, Area Assessment | §5.11 |
| P | Extracted links | **Suggested until an analyst confirms**; source grade visible on every edge; no line without a citation | §5.11 |
| Q | Case access | **Battle Captain or S2 lead opens a case on a person**; viewing role-gated; **every read on the ledger** | §5.11 |
| R | Which views first | **All three together** — link chart, timeline, time wheel — one model, three renderings | §5.11 |
| S | Shift pattern | **Follow-the-sun, three 8 h watches (Singapore · Dublin · San Francisco)** by default; 12 h day/night as the alternative; configurable | `watch.PATTERNS`, `PATCH /watch/config` |
| T | Handover | **Generated brief → outgoing annotates → incoming acknowledges on the ledger; the watch does not transfer until acknowledged** | `/watch/handover`, `/watch/acknowledge` |
| U | Overlap window | **30 minutes**; items arriving inside it are flagged and must be acknowledged by the incoming shift | `build_brief` → `required_item_ids`; `409` on acknowledge |
| V | NSTR | **Explicit** — the outgoing Battle Captain affirms "nothing significant"; the affirmation is logged | `Handover.nstr` → ledger |
| W | Digestibility (2026-09-05) | **Keep the dark monospace wall; fix the hierarchy** — one headline per panel, exceptions as tiles, ratios as bars, cards for what happens, sections headed by their question, color as meaning only. Not a Linear / Vercel restyle; the map stays full width. Rejected as fake instruments: SIGINT waveforms, drone feeds, kill switches, hash-chain badges, invented indices, airframe OR rates without equipment data | §3.2 |
| X | Rated area assessment (2026-09-05) | **Analyst-owned RAG per indicator with one line of why, no composite**; indicator list per profile or `TOC_AREA_INDICATORS`; a new assessment supersedes the last; the strip rides on sites, trips, and events | §5.6, `coptoc/areas.py` |
| Z | Movement grouping (2026-09-05) | **Military: the unit is the actor** — serials by battalion, origin, destination, and a 6 h window. **Corporate: the individual is the actor** — delegations only by a shared destination event; everyone else alone under their name. A VIP never folds; a group needs three. S3 draws all movement, S4 keeps stock and inbound | §3.4, `coptoc/overlays.py` |
| Y | Taskings create things (2026-09-05) | **Collection → operation, supply → shipment, comms / coverage → a task on the subject's operation**; linked both ways so finishing either side completes the other; movement asks create nothing yet | §5.10a, `taskings.on_accept` |

---

## 15. Open Decisions

None outstanding. Everything raised so far is logged in §14; new questions go here as they come up.

## Appendix — Version History

- **v1** — corporate travel-risk platform with a scoring model. Archived as `docs/archive/PRD-v1-travel-risk.md`. The scoring mathematics was invented and is not carried forward.
- **v2** — trust & safety decision support. Archived as `docs/archive/PRD-v2-trust-safety.md`. The evidence discipline is carried forward as the S2 spec.
- **v3** — the TOC as a staff-structured operations center with a common operating picture at its center.
- **v3.1** — S2/S3/S6 built; three decisions taken; data-sources map added; native iOS client.
- **v3.2** — roll-call scope, check-in requests, and restricted-layer roles decided and built (A/B/C).
- **v3.3** — S6 outbound (SMS + chat, real or simulated), check-in links, Battle-Captain-only opening (D/E/F).
- **v3.31** — §3.4 the graphics object: hand-drawn control measures, typed from a per-profile catalog, owned by a section, windowed, retired not deleted; the DRAW tool on the wall; read-only on the phones.
- **v3.30** — §3.4 the section overlays: NAIs from the requirements, threats by age and confirmation with their links, the rating on the site, an S2 time window; movements leg by leg with serials, delegations, individuals, and shipments under the profile's grouping rule; the strip scrub; dim-not-hide on the wall and both phones; decision Z.
- **v3.29** — §3.2 the hierarchy (headline, tiles, bars, cards, questions), §3.3 the strip through NOW with the watch log, the rated area assessment (§5.6, `/v1/cop/areas`), taskings that create operations, shipments, and tasks (§5.10a), rail badges, the context row with sun times, the roll call that takes the wall, red chrome at DEFCON 1, ⌘K; decisions W–Y.
- **v3.28** — §5.10a taskings: the object that carries work between sections, with inbox / outbox and the raise form on every section panel and tab; open taskings in the handover brief.
- **v3.27** — §3.0 the map-first sections: site health from S4/S6 on the model, S4/S6 layers on the wall's map, every phone section tab as the map plus a pull-down sheet.
- **v3.26** — names and ranks (LAST, First M. · RANK on a military desk; pay grades as the constant); sign-in profiles are the roles themselves.
- **v3.25** — §13 the spreadsheet upload: Excel or CSV, header found under title rows, mapping proposed (model or headers), preview then commit; S1 roster builds the task organization from unit paths. Phone SETTINGS as submenus.
- **v3.24** — §9 users and permissions: per-section view/edit, Battle Captain and admin flags, sign-in as a user, the admin's grid; header counters open their section; the phone header floats over the picture (clock left, DEFCON centered, gear right; the watch and counters as a card); the phone dock folds on scroll.
- **v3.23** — the profile: a Military / Corporate menu beside the wordmark that reshapes the sections and reloads the matching sample data; corporate is the product as it was before S4 and S6.
- **v3.22** — the sample force is a Combat Aviation Brigade: task organization on S1 (brigade → battalions → companies) on all three clients; S4 and S6 seeded the way a brigade keeps them (classes of supply, aircraft readiness, PACE per command post). No corporate/military fork.
- **v3.21** — §11.3 settings: keys and options entered from the wall, write-only, encrypted at rest, environment wins; the sources drawer moved under SETTINGS.
- **v3.20** — S4 Logistics and S6 Signal reinstated as background sections for a generic operations center: supply lines, shipments, systems with PACE, roll-ups by exception, panels on the wall and tabs on the phones; the section set as configuration. iOS tab bar drawn by the app.
- **v3.19** — S3 itineraries: optional legs (flight / ground / lodging) on every business trip; the traveler's position follows the current leg; CSV and pasted-confirmation imports; the phone calendar as a continuous day ribbon that unfolds into the month.
- **v3.18** — the wall's layout decided: rails and slide-out panels over the map only, S3 and the log full width; posture as five levels read as DEFCON 5 → 1 with the levels menu; DISPLAY toggles. The recon-diamond identity.
- **v3.17** — the rest of the document: the Warning product with S6 alerting, S1 availability states, NWS zone resolution, export adapters for HRIS / scheduling / travel / calendar / badge, long-range planning with coverage, Wikidata baseline; S2 panels and FLASH on iOS and Android. S4 dropped by the author.
- **v3.16** — §5.10 #3 `Operation` (target package → OPORD) and #4 dissemination tracking built.
- **v3.15** — S6 decisions L–N built: inbound SMS webhook, 15-minute escalation rule, manual roster adds.
- **v3.14** — collectors: USGS, NWS, WHO DON, State Dept, FCDO live and keyless; ACLED and CLSTR behind keys; Nager.Date holiday baseline; country-scoped reporting attaches to requirements by country. ReliefWeb and GDELT deferred with reasons.
- **v3.13** — INTSUM built (§5.6, Decision G): a fixed-order diff since the last one, fixed-hour draft, Battle Captain release.
- **v3.12** — Area Assessment built (§5.6): candidates side by side, reported / quiet / gap cells, refuse-to-approve; stale rulings in §5.6 replaced with G and I.
- **v3.11** — `Report`/`Case` and the case graph built (§5.10 #1–2, §5.11); the review queue is the v1 workbench.
- **v3.10** — Sigtoc requirements, the self-generating collection plan, sources as operator settings, `/v1/s2` embedded and standalone; domains recorded.
- **v3.9** — the watch built: shift model, estimate lines on every panel, the brief, handover/acknowledge on the ledger (web + API; iOS read-only).
- **v3.8** — the watch (§3.1): shift model, panels as running estimates with owned assessment lines, the shift change brief, handover on the ledger; decisions S–V.
- **v3.7** — the analyst's workbench (§5.11): case graph with provenance, suggest→confirm extraction, link chart / timeline / time wheel; decisions O–R.
- **v3.6** — the origin in the author's words (§1.1); the ops↔intel loop and the four requirements it adds (§5.10).
- **v3.5** — cadence adjustable (K); S6 inbound, escalation, roster edits decided (L–N). No open decisions.
- **v3.4** — Sigtoc spec (§5): two missions, first-class requirements, self-generating collection plan, Area Assessment + INTSUM, standalone surface; decisions G–J.
