# TOC Platform — Product Requirements Document (PRD)

**Version:** 0.1 (Draft for Founder Review)  
**Date:** 2026-08-27  
**Author:** Engineering (pending founder approval)

---

## 1. Vision

**TOC (Tactical Operations Center)** is a corporate security intelligence and operations platform that brings military-grade analytical tradecraft to enterprise security teams. It combines two integrated systems:

- **Sigtoc** — An all-source intelligence collection and analysis engine that continuously scans the open-source environment, applies military analytical frameworks (METT-TC, PMESII-PT, IPB, CARVER, ACH), and produces actionable threat assessments powered by AI.

- **Coptoc** — A Common Operating Picture (COP) that displays the current state of the "battlefield" — friendly assets (offices, executives, travelers), active threats (red force indicators), and real-time intelligence overlays — giving the security team a single pane of glass for situational awareness and enforcement.

Together, they form a complete **Intelligence-to-Operations loop**: Sigtoc collects and analyzes; Coptoc displays and enables action.

---

## 2. Problem Statement

Corporate security teams today face fragmented tooling:
- Threat intelligence comes from disparate vendors (Recorded Future, Flashpoint, Dataminr) with no unified analytical layer
- Executive travel risk assessments are manual, ad-hoc processes relying on static State Department advisories
- There is no "Common Operating Picture" — security managers juggle SIEM dashboards, travel trackers, and email chains separately
- Military-grade analytical frameworks (METT-TC, IPB, CARVER) that are battle-proven for threat assessment are not available in any commercial security product
- AI is not applied to continuous environmental scanning — teams are reactive, not proactive

---

## 3. User Personas

### 3.1 The Battle Captain / Shift Manager
**Who:** The security professional running the "watch floor" — monitoring the global security posture in real-time. Former military or law enforcement background common.  
**Needs:** A single screen showing everything: where our people are, where threats are, what changed in the last 8 hours, and what requires immediate action.  
**Frustration:** "I have 6 tabs open across 4 tools and I still don't have a complete picture."

### 3.2 The Intelligence Analyst
**Who:** The analyst tasked with researching threats, writing assessments, and briefing leadership.  
**Needs:** Automated OSINT collection, structured analytical frameworks to organize their analysis, and AI assistance to process large volumes of signals.  
**Frustration:** "I spend 80% of my time collecting data and 20% analyzing it. It should be the opposite."

### 3.3 The Security Director / CISO
**Who:** The executive responsible for global security decisions — approving travel, allocating resources, briefing the C-suite.  
**Needs:** Concise threat assessments tied to specific business decisions (e.g., "Should we send our CEO to Riyadh next month?"). Wants risk scored, not raw data.  
**Frustration:** "Give me a bottom-line assessment with a risk score, not a 40-page report."

### 3.4 The Traveling Executive
**Who:** C-suite or senior leaders who travel internationally to high-risk regions.  
**Needs:** Pre-trip briefing, real-time alerts during travel, and confidence that someone is watching their back.  
**Frustration:** "I found out about the protests near my hotel from Twitter, not from my security team."

---

## 4. Core Capabilities

### 4.1 Sigtoc: Intelligence Collection & Analysis Engine

#### 4.1.1 The Intelligence Cycle

Sigtoc operationalizes the military Intelligence Cycle as a continuous, AI-augmented process:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DIRECTION   │────▶│ COLLECTION  │────▶│ PROCESSING  │
│              │     │             │     │             │
│ PIRs set by  │     │ OSINT, feeds│     │ Structure,  │
│ Security Dir │     │ databases,  │     │ normalize,  │
│              │     │ web research│     │ deduplicate │
└──────────────┘     └─────────────┘     └──────┬──────┘
       ▲                                        │
       │                                        ▼
┌──────┴──────┐                          ┌─────────────┐
│DISSEMINATION│◀─────────────────────────│  ANALYSIS   │
│             │                          │             │
│ COP display,│                          │ METT-TC,    │
│ alerts,     │                          │ PMESII-PT,  │
│ briefings   │                          │ IPB, ACH    │
└─────────────┘                          └─────────────┘
```

#### 4.1.2 Intelligence Collection Disciplines

Sigtoc must support configurable collection sources mapped to intelligence disciplines:

| INT Discipline | Corporate Translation | Example Sources | Collection Method |
| :--- | :--- | :--- | :--- |
| **OSINT** (Open Source) | Publicly available information | News, social media, government filings, SEC, court records | Automated web scanning, RSS, API |
| **CYBINT** (Cyber) | Network and digital intelligence | Dark web forums, paste sites, breach databases | API connectors (Recorded Future, Flashpoint) |
| **GEOINT** (Geospatial) | Location-based intelligence | Satellite imagery, maps, travel advisories | Google Earth API, State Dept API |
| **HUMINT** (Human) | Human source reporting | Executive debriefs, local consultants, industry contacts | Manual entry, structured forms |
| **SIGINT** (Signals) | Communications monitoring (legal) | Social media monitoring, public radio scanners | API (Dataminr, social listening tools) |

> [!IMPORTANT]
> **Source Configuration:** The platform must allow administrators to add, remove, and configure intelligence sources. Not every customer will have Recorded Future or Flashpoint subscriptions. Sources should be pluggable connectors with a standard interface.

#### 4.1.3 Priority Intelligence Requirements (PIRs)

PIRs are the questions that drive the entire system. They flow **top-down** from the
Security Director, and every other component — collection, analysis, scoring, the
refuse-to-score rule — traces back to them.

##### The Decomposition Chain

A PIR is not actionable on its own. The tradecraft is in breaking it apart:

```
PIR (Commander's Question)
 └── SIR (Specific Information Requirement)
      └── Indicator (Observable, Collectible Fact)
           └── Collection Asset (Source + Connector that can observe it)
```

**PIR → SIR:** A PIR is decomposed into Specific Information Requirements — the
sub-questions that, if collectively answered, would answer the PIR. A PIR typically
produces 3–7 SIRs. If it produces more, the PIR is too broad.

**SIR → Indicator:** Each SIR is decomposed into observable indicators — concrete,
collectible facts that would constitute evidence. Indicators must be specific enough
that a collector (human or automated) knows what to look for. "Increased threat
activity" is not an indicator. "Named groups claiming responsibility for attacks
against Western nationals in the AO within the last 90 days" is an indicator.

**Indicator → Collection Asset:** Each indicator is mapped to one or more collection
assets — the specific `Source` entities (§7.1) that can observe it. This mapping is
the synchronization matrix.

##### Worked Example

**PIR:** *"Are there active kidnapping-for-ransom threats targeting Western executives
in Mexico City within the next 90 days?"*

| SIR | Indicators | Collection Assets |
| :--- | :--- | :--- |
| **SIR 1:** Which criminal organizations are conducting KFR operations in the Mexico City metro area? | Named groups in law enforcement reports; arrest records identifying KFR cells; ransom payment patterns | OSINT (OSAC reports, local news), HUMINT (local security consultant) |
| **SIR 2:** Have any groups specifically targeted foreign business travelers (vs. local targets)? | Reports of foreign-national kidnappings; dark web/forum chatter mentioning corporate targets; historical victim profiles | CYBINT (dark web monitoring), OSINT (news, embassy warden messages) |
| **SIR 3:** What is the current security-force posture for VIP protection in the area? | Federal police deployments; military checkpoints; embassy security notice cadence | OSINT (embassy notices), GEOINT (mapping security infrastructure) |
| **SIR 4:** Are there environmental factors that increase KFR risk during the travel window? | Upcoming elections or political transitions; cartel territorial disputes; economic downturn indicators | OSINT (news, GDELT event data) |

##### The Synchronization Matrix

The synchronization matrix is the operational artifact that maps every indicator to a
collection asset, assigns a collection frequency, and tracks fulfillment status. It is
the mechanism that turns PIRs into collection tasking.

| Indicator | Collection Asset (Source) | Frequency | Last Collected | Status |
| :--- | :--- | :--- | :--- | :--- |
| Named KFR groups in LE reports | OSAC Mexico (OSINT, A2) | Weekly | 2026-08-20 | ✅ Current |
| Foreign-national kidnapping reports | News RSS — Mexico (OSINT, C3) | Daily | 2026-08-27 | ✅ Current |
| Dark web chatter re: corporate targets | Flashpoint Mexico feed (CYBINT, B2) | Daily | 2026-08-27 | ✅ Current |
| Security-force deployment posture | Local security consultant (HUMINT, C4) | Biweekly | 2026-08-14 | ⚠️ Due |
| Embassy security notice cadence | State Dept RSS (OSINT, A1) | Daily | 2026-08-27 | ✅ Current |
| Cartel territorial disputes | ACLED Mexico (OSINT, B2) | Weekly | 2026-08-22 | ✅ Current |

The `(OSINT, A2)` notation is the source's discipline and Admiralty reliability rating
from §6.5. Collection frequency depends on the indicator's volatility and the
dimension's half-life from §6.2.

##### Connection to §6: The Refuse-to-Score Bridge

This is where PIRs and scoring talk to each other:

1. Each **SIR** maps to one or more **risk dimensions** from §6.2. SIR 1 and SIR 2
   feed the Violent Crime / KFR dimension. SIR 3 feeds the Terrorism dimension
   (security-force posture is a mitigating factor). SIR 4 feeds Civil Unrest.

2. Each **indicator** produces **Signals** (§7.1). Signals feed **Events**. Events
   produce **Evidence** rows linked to **DimensionScores**.

3. A PIR whose SIRs have **no fulfilled indicators** for a dimension means that
   dimension has zero `Evidence` rows → `INSUFFICIENT` confidence → and if that
   dimension carries ≥20% of mission weight, the **refuse-to-score rule** (§6.6) fires.

4. The synchronization matrix status column is the early warning system. When an
   indicator goes stale (past its collection cadence), the analyst sees a gap *before*
   the refuse-to-score rule blocks the assessment.

This chain — PIR → SIR → Indicator → Signal → Event → Evidence → DimensionScore →
Assessment — is the traceability spine of the entire platform. Every number in a
published assessment can be walked backward through it to a dated, sourced observation.

##### PIR Lifecycle

| Status | Meaning |
| :--- | :--- |
| **ACTIVE** | Collection is being directed against this PIR's indicators |
| **ANSWERED** | All SIRs have sufficient evidence; assessment published |
| **EXPIRED** | The decision window has passed (e.g., trip completed, event concluded) |
| **SUSPENDED** | Temporarily deprioritized — collection assets reallocated |

PIRs are not permanent. They are tied to pending decisions. A PIR without an expiration
date or a decision it informs is not a PIR — it is a standing collection requirement,
which is a different (and lower-priority) object.

##### FFIRs: The Other Half of CCIR

The data model (§7.1) includes `Requirement` with `kind = PIR | FFIR`. **Friendly
Force Information Requirements** are the questions the Battle Captain needs answered
about *our own forces*:

- "Has the traveling executive checked in from their hotel?"
- "Is the Mexico City office badge system showing normal access patterns?"
- "Did the EP team confirm their advance on the meeting venue?"

FFIRs are as critical as PIRs on the watch floor — an unanswered FFIR about a
traveler's status in a high-risk zone can escalate faster than most PIR-driven threats.

#### 4.1.4 Directed Threat Assessments (Executive Travel)

**Use Case:** "Our CEO needs to travel to Riyadh, Saudi Arabia next month. What's the risk?"

Sigtoc generates a structured threat assessment using military frameworks:

**METT-TC Analysis (adapted for executive travel):**

| Factor | Corporate Translation | Example Output |
| :--- | :--- | :--- |
| **Mission** | Business purpose of the trip | "Board meeting with Aramco leadership, 3-day stay" |
| **Enemy** | Active threats in the region | "Iranian-backed militia activity: LOW direct threat to Western business travelers. Houthi drone/missile attacks on infrastructure: MODERATE." |
| **Terrain** | Physical & regulatory environment | "Modern urban infrastructure, extreme heat (45°C), strict local laws on speech/conduct, reliable medical facilities" |
| **Troops** | Security resources available | "Executive protection vendor available (GardaWorld), hotel security team vetted, embassy RSO contact established" |
| **Time** | Timing considerations | "Trip coincides with Hajj season — increased security presence but also increased targeting risk" |
| **Civil** | Cultural & social considerations | "Dress code requirements, Ramadan considerations, gender-specific protocols" |

**PMESII-PT Analysis (country-level context):**

| Factor | Assessment |
| :--- | :--- |
| **Political** | Stable monarchy, Vision 2030 reforms, normalized relations with Israel (Abraham Accords) |
| **Military** | Active conflict in Yemen, internal security forces well-resourced |
| **Economic** | Oil-dependent but diversifying, major construction projects |
| **Social** | Rapid modernization, but conservative social norms |
| **Information** | Controlled media environment, social media monitored |
| **Infrastructure** | Modern airports, hotels, hospitals; Neom construction zone |
| **Physical Environment** | Desert climate, extreme heat June-September |
| **Time** | 90-day assessment window |

**Additional layers:**
- **State Department Advisory Level:** Level 2 — Exercise Increased Caution
- **Espionage Risk:** MODERATE — Saudi intelligence services conduct surveillance of foreign business visitors
- **Terrorism Risk:** LOW in Riyadh (higher in eastern/southern provinces)
- **Overall Risk Score:** 3.2 / 5.0 (Moderate)
- **Recommendation:** APPROVE with enhanced security protocols

#### 4.1.5 Continuous Environmental Scanning

Sigtoc runs daily automated OSINT collection cycles:
- Scans news sources, government advisories, and social media for changes relevant to PIRs
- Monitors threat actor channels (Telegram, dark web forums) for emerging campaigns
- Tracks geopolitical developments in countries where the company has assets or travel
- AI analyzes collected signals against active PIRs and generates daily intelligence summaries
- Flags significant changes for analyst review

#### 4.1.6 Analytical Frameworks (AI-Assisted)

The analyst selects a framework; AI assists with structuring the analysis:

| Framework | Use Case | When to Use |
| :--- | :--- | :--- |
| **METT-TC** | Tactical risk assessment | Executive travel, event security, facility opening |
| **PMESII-PT** | Strategic country/region analysis | Market entry, long-term risk posture |
| **IPB** | Threat modeling | "What will the adversary do and where?" |
| **CARVER** | Asset prioritization | "Which of our facilities is most vulnerable?" |
| **ACH** | Competing hypothesis analysis | "Was this incident an insider threat or external hack?" |
| **ASCOPE** | Stakeholder & civil environment mapping | New office location, community risk |

#### 4.1.7 Intelligence Output Products

The PRD defines frameworks and scoring, but the analyst and the Security Director
don't consume frameworks — they consume **artifacts on a page**. Every output product
follows the same structure: **BLUF first, evidence second, gaps last.**

##### BLUF-First Assessment Structure

Every assessment — regardless of framework — renders in this order:

1. **BLUF (Bottom Line Up Front):** One to three sentences. The answer. The score.
   The recommendation. The Security Director reads this and nothing else unless they
   want to.
2. **Key Judgments:** 3–5 numbered sentences, each with its estimative probability
   term and analytic confidence. These are the claims the assessment is making.
3. **Dimension Detail:** The per-dimension breakdown from §6.2, with scores, evidence
   citations, and collection gaps.
4. **Mitigations & Residual Risk:** Inherent vs. residual scoring from §6.4, with
   specific mitigation credits applied.
5. **Collection Gaps:** What we *don't know*, expressed as unfulfilled indicators from
   the synchronization matrix (§4.1.3). This is the most important section after BLUF
   — it is what prevents the assessment from overstating its confidence.

##### Product Catalog

| Product | Military Equivalent | Purpose | Cadence | Author |
| :--- | :--- | :--- | :--- | :--- |
| **Travel Risk Assessment** | — | BLUF + METT-TC/PMESII for a specific trip | Per-trip | AI drafts → analyst reviews |
| **Daily Intelligence Summary** | INTSUM | What changed in the last 24 hours across all active PIRs. New signals, updated scores, collection gaps. | Daily, 0600 local | AI drafts → analyst reviews |
| **Situation Report** | SITREP | Current status of an ongoing incident or developing situation. Point-in-time snapshot. | As-needed | Analyst authors |
| **Threat Warning** | WARNORD | Specific, imminent, actionable threat requiring immediate decision. FLASH-priority. | Immediate | AI flags → analyst verifies → Battle Captain disseminates |
| **Weekly Strategic Brief** | — | Trend analysis, PIR status, collection gap summary, risk posture changes. For Security Director / C-suite. | Weekly | Analyst authors |
| **Country / Region Profile** | IPB Product | Standing reference for a country or region. Slow-moving baseline. | Quarterly refresh | AI drafts → analyst reviews |

##### The INTSUM Format

The Daily Intelligence Summary follows a fixed structure so the Battle Captain at
shift change can consume it in under 5 minutes:

```
DAILY INTELLIGENCE SUMMARY — [DATE] 0600 ET
Classification: UNCLASSIFIED // COMPANY PROPRIETARY

1. BLUF
   [2–3 sentences: most significant change in the last 24 hours]

2. PIR STATUS
   PIR-001: [question] ............... ACTIVE — no change
   PIR-002: [question] ............... UPDATED — new signals (see §4)
   PIR-003: [question] ............... COLLECTION GAP (see §6)

3. SIGNIFICANT SIGNALS (last 24h)
   [timestamp] [source rating] [headline] [dimension affected]
   [timestamp] [source rating] [headline] [dimension affected]

4. SCORE CHANGES
   [asset/trip] [dimension] [old → new] [reason]

5. ACTIVE TRAVEL
   [traveler] [location] [risk band] [next milestone]

6. COLLECTION GAPS
   [indicator] [last collected] [days overdue] [impact]
```

#### 4.1.8 AI Job Boundary

The AI operates at **Level 2 autonomy**: it drafts, humans approve. But "Level 2"
is insufficiently precise. The boundary is defined by what the model **may** and
**may not** do.

##### The Model May:

- **Extract** structured facts from unstructured text (named entities, dates,
  locations, event types, casualty counts)
- **Classify** events into the dimension taxonomy from §6.2
- **Compute** severity scores using the fixed rubric per event type — the rubric is
  code, the model applies it
- **Draft** assessments using the BLUF-first structure and the selected analytical
  framework
- **Select** an estimative probability term from the seven ICD 203 terms in §6.5.1
  — but only from the fixed list, never inventing phrasing
- **Identify** collection gaps by comparing indicator requirements against fulfilled
  signals
- **Propose** SIR decompositions when an analyst creates a new PIR

##### The Model May Not:

- **Assign** source reliability ratings (Admiralty A–F) — this is a property of the
  source's track record, set by an analyst
- **Grade** its own analytic confidence — confidence is computed by code from the
  evidence chain (number of independent sources, corroboration, staleness), not
  asserted by the model
- **Override** the refuse-to-score rule — if evidence is `INSUFFICIENT`, the model
  cannot fill the gap with its parametric knowledge
- **Invent** estimative language — it may not say "highly probable" or "almost
  impossible" or any phrasing not in the ICD 203 table
- **Make** recommendations — the model populates the scoring framework; the
  recommendation (approve, defer, deny) is derived by code from the score bands in
  §6.7, not chosen by the model
- **Publish** anything without a human moving the assessment from `draft` to
  `in_review` to `approved` (§7.1 Assessment status)

##### Why This Boundary

The boundary is not about distrust of AI. It is about **auditability**. When the
Security Director asks "why did we approve this trip," the answer must trace to dated
evidence through deterministic scoring — not to "the model thought it was fine." The
model is a productivity tool for the analyst, not a decision-maker. The decision-maker
is the human whose name is on the assessment's `reviewer_id` and `approved_at` fields.

---

### 4.2 Coptoc: Common Operating Picture & Enforcement

#### 4.2.1 The COP Dashboard (Blue Force Tracker)

A map-based visual interface showing the current state of the "battlefield":

**Blue Force (Friendly Assets):**
- 📍 Office locations pinned on the map (SF, NYC, DC, London, etc.)
- 🧑‍💼 Traveling executives / employees with real-time or last-known location
- 🏢 Data centers, warehouses, key vendor locations
- Status indicators: Normal (green), Elevated (yellow), Critical (red)

**Red Force (Threat Indicators):**
- 🔴 Active threat zones (protests, conflict, natural disasters)
- ⚠️ Threat actor activity regions (from Sigtoc intel)
- 🎯 Specific threats directed at company assets
- Threat severity overlay (heat map)

**Operational Overlays:**
- State Department travel advisory levels by country (color-coded)
- Active PIR coverage areas
- Current executive travel routes and itineraries
- Weather/natural disaster warnings

#### 4.2.2 Operations Feed

A chronological feed (like a military operations log / "Battle Log") showing:
- New intelligence from Sigtoc (alerts, assessments)
- Status changes (threat level changes, advisory updates)
- Actions taken (travel approved/denied, security posture changes)
- Shift handover notes from the Battle Captain

#### 4.2.3 Content Moderation / Policy Enforcement (Existing Engine)

The existing T&S Policy-as-Code engine (already built) handles:
- Policy-as-Code compilation (YAML → classifier prompts)
- Severity × Confidence routing matrix
- Reach gates for escalating review
- Anti-brigading report aggregation
- Immutable audit ledger

> [!NOTE]
> **Relationship to the COP:** The content moderation engine is a specialized enforcement module. For companies that also operate consumer platforms (like SoriStory), moderation decisions and trends can be displayed as an overlay on the COP — showing content policy violations as another signal alongside physical and cyber threats.

---

## 5. The Intel-to-Operations Loop

This is the core differentiator — intelligence doesn't just get collected, it drives action:

```
┌─────────────────────────────────────────────────────────┐
│                    SIGTOC (Intelligence)                 │
│                                                         │
│  PIRs ──▶ Collection ──▶ Analysis ──▶ Threat Reports   │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ Policy Overlays, Alerts, Assessments
                         │
┌────────────────────────┴────────────────────────────────┐
│                    COPTOC (Operations)                   │
│                                                         │
│  COP Dashboard ◀── Blue/Red Force ◀── Threat Overlays  │
│  Ops Feed      ◀── Alerts         ◀── Travel Decisions │
│  Enforcement   ◀── Policy Updates ◀── Reach Gates      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Example flow:**
1. Security Director sets PIR: "Monitor Iran-backed threat activity near our Dubai office"
2. Sigtoc collects daily OSINT on the topic, analyzes using IPB framework
3. Sigtoc detects increased militia rhetoric targeting Western businesses in Gulf states
4. Alert fires → appears on Coptoc COP dashboard as a red overlay near Dubai
5. Battle Captain sees alert, escalates to Security Director
6. Security Director decides to elevate Dubai office to "heightened" posture
7. Traveling executive's upcoming Dubai trip is flagged for enhanced EP protocols
8. All actions logged in the operations feed

---

## 6. Threat Scoring Model

> The Overall Risk Score is the product. Everything else is packaging around it. This
> section defines where the number comes from, so that no assessment ever contains a
> figure that cannot be traced to dated evidence.

### 6.1 Design Principles

1. **Derived, never asserted.** The AI does not "decide" a risk score. It extracts and
   grades evidence; the score is computed from that evidence by deterministic code.
2. **Absence of evidence is not evidence of safety.** A dimension with no collection
   returns `INSUFFICIENT`, not a low score.
3. **Inherent before residual.** Report risk before and after mitigations, so the
   Security Director can see what their security spend actually buys.
4. **Uncertainty is expressed to a standard.** Confidence is graded and stated using
   ICD 203 estimative language, not adjectives chosen by a language model.

### 6.2 Risk Dimensions

Every assessment scores eight dimensions on a 0–5 scale.

| # | Dimension | Primary Free Sources | Signal Half-Life |
| :-- | :--- | :--- | :--- |
| 1 | **Civil Unrest** | ACLED, GDELT, news RSS | 30 days |
| 2 | **Terrorism / Targeted Violence** | GTD, ACLED, State Dept | 90 days |
| 3 | **Violent Crime / KFR** | State Dept, OSAC, UNODC | 180 days |
| 4 | **Espionage / Device Compromise** | State Dept, CISA, NCSC advisories | 365 days |
| 5 | **Health & Medical** | WHO, CDC travel notices | 60 days |
| 6 | **Natural Hazards** | GDACS, USGS, NOAA | 14 days |
| 7 | **Legal & Detention Risk** | State Dept, wrongful-detention listings | 365 days |
| 8 | **Infrastructure & Mobility** | OSM, aviation notices, outage trackers | 30 days |

Half-lives differ because the phenomena differ. A protest three weeks ago is highly
predictive of a protest tomorrow; a counterintelligence posture three weeks ago is
just the counterintelligence posture.

### 6.3 Dimension Score

For dimension `i`:

```
d_i = clamp( base_i + delta_i , 0 , 5 )
```

**`base_i` — the standing baseline.** Mapped from slow-moving authoritative sources
(e.g. State Dept advisory level 1–4 → 0.5/1.5/3.0/4.5). This is what the dimension
scores when nothing is happening.

**`delta_i` — the event signal**, bounded to `[-1.0, +2.0]`. Recent, nearby,
well-sourced events push the score up; a sustained quiet period relieves it slightly.

```
delta_i = 3.0 * tanh( sum_over_events( sev_e * recency_e * proximity_e * rating_e ) ) - 1.0
```

| Term | Definition |
| :--- | :--- |
| `sev_e` | Event severity, 0–1, from a fixed rubric per event type (not model judgment) |
| `recency_e` | `0.5 ^ (age_days / half_life_i)` — per-dimension half-life from §6.2 |
| `proximity_e` | `exp( -(dist_km^2) / (2 * sigma_i^2) )` against the nearest itinerary point |
| `rating_e` | Admiralty rating of the reporting signal, 0–1 — two axes, see §6.5 |

Proximity `sigma_i` is dimension-specific: 25 km for unrest, 50 km for terrorism,
country-wide for espionage and legal risk. A riot 400 km from the hotel is context,
not a threat to this trip, and the math should say so.

### 6.4 Composite Score

**Inherent Risk** is a mission-weighted mean. Weights come from the trip profile —
a factory site visit weights infrastructure and crime; a public keynote weights
terrorism and unrest.

```
Inherent = sum( w_i * d_i ) / sum( w_i )
```

**Residual Risk** applies mitigation credits multiplicatively, floored so that no
amount of security spending drives risk to zero.

```
Residual = max( Inherent * product( 1 - credit_j ) , 0.4 * Inherent )
```

| Mitigation | Credit | Dimensions Affected |
| :--- | :--- | :--- |
| Executive protection detail | 0.30 | Crime, Terrorism |
| Vetted secure transport | 0.20 | Crime, Infrastructure |
| Clean-device / loaner protocol | 0.45 | Espionage |
| Vetted hotel with standoff | 0.15 | Terrorism, Crime |
| Local fixer / legal counsel on retainer | 0.25 | Legal |

Only credits for dimensions actually carrying weight are applied — a clean-device
protocol does not reduce a hurricane.

### 6.5 The Three Confidence Axes

> [!IMPORTANT]
> Every intelligence product in this system states **source reliability**, **information
> credibility**, and **analytic confidence** separately, and never derives one from
> another. Collapsing them is the most common way a competent-looking assessment
> becomes misleading.

**Axis 1 — Source Reliability (Admiralty A–F).** A property of the *source*, assigned
from its track record, independent of any particular report.

| Grade | Meaning |
| :--- | :--- |
| **A** | Completely reliable — no history of failure |
| **B** | Usually reliable — minor doubts, mostly valid history |
| **C** | Fairly reliable — some doubts, has provided valid information |
| **D** | Not usually reliable — significant doubts, occasional valid information |
| **E** | Unreliable — history of invalid information |
| **F** | Cannot be judged — no basis for assessment (new or unknown source) |

**Axis 2 — Information Credibility (Admiralty 1–6).** A property of *this specific
report*, assessed on its own merits and corroboration.

| Grade | Meaning |
| :--- | :--- |
| **1** | Confirmed by independent sources |
| **2** | Probably true — logical, consistent with other information |
| **3** | Possibly true — reasonably logical, agrees with some other information |
| **4** | Doubtful — possible but not confirmed, no other agreeing information |
| **5** | Improbable — contradicted by other information |
| **6** | Cannot be judged — no basis for assessment |

Together these produce the standard two-character rating: a `B2` from a usually-reliable
source reporting probably-true information. Note that **`E` and `F` are not the same
thing** — a source with a record of falsehood is worse than an unknown source — and the
weighting must reflect that. Likewise `5` (contradicted) is worse than `6` (unverifiable).

The scalar `rating_e` used in §6.3 is the geometric mean of the two axis weights, so
that a strong reading on one axis is discounted but not annihilated by an unknown on
the other. An `A6` — an excellent source reporting something nobody can corroborate —
is worth something. It is not worth nothing, and it is not worth an `A1`.

**Axis 3 — Analytic Confidence (ICD 203).** A property of *our judgment*, not of any
source. It answers: how much would we bet on this assessment being right?

| Confidence | Basis |
| :--- | :--- |
| **High** | ≥3 independent sources, at least one rated `B2` or better, no unresolved contradictions, evidence within the dimension's half-life |
| **Moderate** | ≥2 independent sources, at least one rated `C3` or better, contradictions identified and explained |
| **Low** | Single source, or unresolved source conflict, or all evidence rated `D4` or worse, or evidence stale relative to half-life |
| **INSUFFICIENT** | No qualifying evidence — the dimension is not scored |

"Independent" means distinct origin, not distinct URL. Forty outlets republishing one
wire report is one source, and the deduplication in §7.1 must collapse them before
confidence is computed.

### 6.5.1 Confidence Is Not Probability

ICD 203 separates these and so does this platform. **Analytic confidence** describes the
strength of our evidence and reasoning. **Estimative probability** describes how likely
the thing is to happen. They vary independently — high confidence that an event is very
unlikely is a completely coherent, and common, assessment.

Forecast statements use only these terms, with their fixed numeric ranges:

| Term | Range |
| :--- | :--- |
| almost no chance | 01–05% |
| very unlikely | 05–20% |
| unlikely | 20–45% |
| roughly even chance | 45–55% |
| likely | 55–80% |
| very likely | 80–95% |
| almost certain | 95–99% |

Every generated judgment renders both axes explicitly, in this form:

> *"Sustained civil unrest within 25 km of the itinerary is **unlikely** (20–45%) during
> the travel window. **Moderate confidence** — two independent sources rated B2 and C3;
> no reporting on security-force posture, which is the primary gap."*

The model is never permitted to invent an estimative term. It selects from the seven
above, and the numeric band is attached by code.

### 6.6 The Refuse-to-Score Rule

> [!IMPORTANT]
> If dimensions carrying more than 20% of total mission weight return `INSUFFICIENT`,
> the platform does **not** emit an Overall Risk Score. It emits a collection gap:
> *"Assessment incomplete — no qualifying collection on Espionage and Legal Risk, which
> carry 35% of mission weight for this trip profile."*
>
> This is the single most important behavior in the product. A travel-risk platform that
> produces a confident, well-formatted number from thin air is worse than no platform,
> because it launders a guess into an artifact that looks like analysis.

### 6.7 Score Presentation

Scores render as a band, never a bare decimal, and always adjacent to their confidence:

| Residual | Band | Default Recommendation |
| :--- | :--- | :--- |
| 0.0 – 1.5 | **LOW** | Approve — standard protocols |
| 1.5 – 2.5 | **GUARDED** | Approve — brief traveler on flagged dimensions |
| 2.5 – 3.5 | **MODERATE** | Approve with enhanced protocols (list required mitigations) |
| 3.5 – 4.3 | **HIGH** | Director decision required — defer if business purpose permits |
| 4.3 – 5.0 | **SEVERE** | Recommend against travel |

The recommendation is a default, not a decision. The Director's override — and their
stated reasoning — is written to the ledger alongside it.

---

## 7. Data Model

Twelve entities. The design goal is that **every number in a published assessment can be
walked back to a raw collected signal with a URL and a timestamp.**

### 7.1 Entities

**Collection side — append-only, never edited:**

| Entity | Key Fields | Notes |
| :--- | :--- | :--- |
| `Source` | `source_id`, `name`, `discipline`, `reliability` (A–F), `connector_class`, `enabled` | Pluggable per §4.1.2. Reliability is axis 1 (§6.5) and belongs to the source, not the report. |
| `Signal` | `signal_id`, `source_id`, `credibility` (1–6), `raw_text`, `url`, `published_at`, `collected_at`, `geo`, `content_hash`, `origin_key` | Immutable. The atom of the system. Credibility is axis 2 and belongs to the report. `origin_key` collapses syndicated republication so independence counts are honest. |
| `Event` | `event_id`, `signal_ids[]`, `event_type`, `severity`, `geo`, `occurred_at`, `entity_ids[]` | A structured fact extracted from one or more signals. This is where AI does its work — extraction, not judgment. |

**Subject side — what we are protecting:**

| Entity | Key Fields | Notes |
| :--- | :--- | :--- |
| `Asset` | `asset_id`, `type` (office/dc/vendor), `geo`, `criticality`, `posture` | Blue force pins on the COP. |
| `Person` | `person_id`, `role`, `sensitivity_tier`, `public_profile` | Sensitivity tier drives access control and the traveler profile multiplier. |
| `Trip` → `ItineraryLeg` | `trip_id`, `person_id`, `purpose`, `mission_profile` / `leg_id`, `geo`, `arrive_at`, `depart_at` | Legs are what §6.3 proximity is measured against. |

**Direction side — the PIR decomposition chain from §4.1.3:**

| Entity | Key Fields | Notes |
| :--- | :--- | :--- |
| `Requirement` | `req_id`, `kind` (`PIR`/`FFIR`), `question`, `owner_id`, `priority`, `geo_scope`, `expires_at`, `status` | Status: `ACTIVE` / `ANSWERED` / `EXPIRED` / `SUSPENDED`. FFIRs are the missing half of CCIR — "an executive has gone dark," "a site lost comms" — and are as much of the watch floor's job as PIRs. |
| `SIR` | `sir_id`, `req_id`, `question`, `dimensions[]`, `status` | Specific Information Requirement. `dimensions[]` maps this SIR to one or more risk dimensions from §6.2, connecting the PIR chain to the scoring chain. |
| `Indicator` | `indicator_id`, `sir_id`, `description`, `observable_pattern`, `volatility` | The collectible fact. `volatility` drives collection frequency in the synchronization matrix. |
| `CollectionTasking` | `tasking_id`, `indicator_id`, `source_id`, `frequency`, `last_collected_at`, `status` | The synchronization matrix row. Status: `CURRENT` / `DUE` / `OVERDUE` / `GAP`. An `OVERDUE` tasking is the early warning that the refuse-to-score rule (§6.6) is about to fire. |

**Analysis side — the part that gets published:**

| Entity | Key Fields | Notes |
| :--- | :--- | :--- |
| `Assessment` | `assessment_id`, `subject_type` (trip/asset/region), `subject_id`, `framework`, `inherent_score`, `residual_score`, `analytic_confidence`, `status`, `author`, `reviewer_id`, `approved_at` | Status: `draft` → `in_review` → `approved` → `superseded`. AI authors drafts; only a human moves it past `in_review` (§4.1.8). |
| `DimensionScore` | `assessment_id`, `dimension`, `base`, `delta`, `value`, `analytic_confidence`, `weight` | One row per dimension in §6.2. Stores the inputs, not just the output. |
| `Evidence` | `dimension_score_id`, `event_id`, `contribution`, `quote`, `retrieved_at` | **The join table that makes the whole thing honest.** A `DimensionScore` with zero `Evidence` rows is `INSUFFICIENT` by definition — traceability is enforced by the schema, not by discipline. |

### 7.2 Relationships

```
                        DIRECTION (PIR Decomposition)
                        ─────────────────────────────
Requirement ──1:N──▶ SIR ──1:N──▶ Indicator ──1:N──▶ CollectionTasking
    │                  │                                    │
    │                  │ dimensions[]                       │ source_id
    │                  ▼                                    ▼
    │             DimensionScore                         Source
    │                  ▲                                    │
    │                  │                                    │
    │           ANALYSIS                          COLLECTION
    │           ────────                          ──────────
    │      Assessment ──1:N──▶ DimensionScore     Source ──1:N──▶ Signal
    │           ▲              ──1:N──▶ Evidence               ──N:M──▶ Event
    │           │                        │                         │
    │     subject_of                     └─────── event_id ───────┘
    │           │
    └──── Trip ──1:N──▶ ItineraryLeg
              │
    Person ───┘
    Asset ──subject_of──▶ Assessment ──emits──▶ LedgerEvent
```

Key join paths:
- **Traceability**: Assessment → DimensionScore → Evidence → Event → Signal → Source
- **PIR fulfillment**: Requirement → SIR → Indicator → CollectionTasking (status = OVERDUE → refuse-to-score)
- **Proximity scoring**: ItineraryLeg.geo ↔ Event.geo (§6.3 distance calculation)

### 7.3 Reuse of the Existing Ledger

[`event_stream.py`](apps/coptoc/src/coptoc/ledger/event_stream.py) already implements a
hash-chained append-only ledger for moderation decisions. It is the correct primitive
here without modification: every `Assessment` status transition, every Director
override of a recommendation, and every mitigation credit applied is written as a
`LedgerEvent` with `prev_hash` chaining.

This is the one genuine shared component between the moderation engine and the COP —
and it is the more valuable of the two uses. "Who approved sending the CEO to Riyadh,
on what evidence, at what time, and can you prove the record wasn't altered" is
exactly what a hash-chained ledger is for.

---

## 8. Decisions Log

> [!NOTE]
> All open questions have been resolved. This section records the decisions for reference.

| # | Question | Decision | Reference |
| :--- | :--- | :--- | :--- |
| Q1 | Product Scope — Two Products or One? | One platform. T&S engine is a module within the COP; moderation decisions are another signal alongside physical/cyber threats. Hash-chained ledger is the genuine shared component. | §4.2.3, §7.3 |
| Q2 | MVP Scope — What Ships First? | **Option A: Sigtoc intelligence engine (CLI/API), focused on the Directed Travel Risk Assessment.** The scoring model, PIR decomposition, refuse-to-score, and AI-assisted METT-TC are the moat. COP dashboard is a thin visual layer added after the engine works. | See below |
| Q3 | AI Role | **Level 2:** AI drafts, humans approve. Explicit may/may-not boundary codified. | §4.1.8 |
| Q4 | Data Sources | **Tier 1 (MVP):** State Dept, GDELT, WHO/CDC, GDACS. **Tier 2 (post-MVP):** ACLED, CISA, news RSS, MITRE ATT&CK. **Tier 3 (premium):** Recorded Future, Flashpoint, Dataminr, Mandiant. | See below |
| Q5 | Additional Frameworks | INTSUM, SITREP, WARNORD, Weekly Brief, Country Profile defined as first-class output products. BLUF-first structure for all artifacts. | §4.1.7 |

### Q2 Decision Detail: MVP Scope

The MVP exercises the full intelligence chain for one use case — **Directed Travel Risk Assessment**:

1. Security Director creates a PIR tied to a planned trip
2. System decomposes into SIRs and maps indicators to collection assets
3. Collectors pull from 4 Tier 1 OSINT sources (State Dept, GDELT, WHO/CDC, GDACS)
4. AI extracts events, maps to dimensions, computes scores using §6 model
5. AI drafts BLUF-first assessment using METT-TC / PMESII-PT framework
6. Refuse-to-score fires on dimensions with insufficient evidence
7. Analyst reviews, sets source reliability ratings, approves
8. Assessment published with full evidence traceability
9. All status transitions logged to hash-chained ledger

**Not in MVP:** COP dashboard, Blue Force Tracker map, incident management, alerting tiers, content moderation integration. These are Phase 2+.

### Q4 Decision Detail: Data Source Tiers

**Tier 1 — Ship with MVP (4 sources, 6 of 8 dimensions covered):**

| Source | Dimensions | Admiralty Rating | Access Method |
| :--- | :--- | :--- | :--- |
| US State Department Travel Advisories | Unrest, Terrorism, Crime, Espionage, Legal | A2 (gov, structured) | Consular API / scrape |
| GDELT | Civil Unrest, Terrorism | B3 (aggregated, noisy) | BigQuery / file download |
| WHO / CDC Travel Health Notices | Health & Medical | A1 (authoritative) | RSS / API |
| GDACS | Natural Hazards | A1 (UN-operated) | XML / RSS API |

**Uncovered dimensions (by design):** Espionage/Device Compromise and Infrastructure/Mobility have only partial State Dept coverage. The refuse-to-score rule will fire on these for most destinations — and that is correct behavior. A free platform that admits "we lack espionage collection on this country" is more honest than a paid platform that fabricates confidence.

**Tier 2 — Post-MVP:** ACLED, CISA/US-CERT, News RSS, MITRE ATT&CK.  
**Tier 3 — Open-Core Premium:** Recorded Future, Flashpoint, Dataminr, Mandiant.
