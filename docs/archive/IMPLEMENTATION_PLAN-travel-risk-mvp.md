# Implementation Plan: TOC MVP — Sigtoc Intelligence Engine

**PRD Reference:** [PRD.md](file:///Users/h4yd3n/Apps/TOC/PRD.md)  
**MVP Scope:** Directed Travel Risk Assessment via CLI/API (PRD §8, Q2)  
**Existing Codebase:** `/Users/h4yd3n/Apps/TOC` — existing T&S engine preserved in `apps/coptoc`, Sigtoc internals reworked

---

## Relationship to Existing Code

The existing codebase has a working T&S engine (Coptoc) and a stub intelligence pipeline (Sigtoc). This plan:

- **Preserves** `apps/coptoc/` entirely — it's not in MVP scope but remains functional
- **Reworks** `apps/sigtoc/` — replaces the stub connectors, scorer, and graph with the PRD-defined intelligence engine
- **Reworks** `packages/shared/` — replaces the Pydantic models with the 12-entity data model from PRD §7
- **Reuses** the hash-chained ledger (`event_stream.py`) and SQLAlchemy infrastructure (`database.py`)
- **Reuses** the Claude classifier client pattern (dual-mode: heuristic fallback + real API)

---

## Phase 1: Data Model & Foundation

> PRD §7.1 — Twelve entities. Every number in a published assessment traces to a dated, sourced observation.

### Shared Models

#### [MODIFY] [models.py](file:///Users/h4yd3n/Apps/TOC/packages/shared/src/shared/models.py)
Replace existing models with the 12-entity PRD data model. Keep existing T&S models (ContentItem, ModerationDecision, etc.) in a separate `ts_models.py` so Coptoc still works.

**Collection side (append-only):**
- `Source` — `source_id`, `name`, `discipline` (OSINT/CYBINT/GEOINT/HUMINT/SIGINT), `reliability` (A-F), `connector_class`, `enabled`
- `Signal` — `signal_id`, `source_id`, `credibility` (1-6), `raw_text`, `url`, `published_at`, `collected_at`, `geo` (lat/lon), `content_hash`, `origin_key`
- `Event` — `event_id`, `signal_ids[]`, `event_type`, `severity` (0-1), `geo`, `occurred_at`, `entity_ids[]`

**Subject side:**
- `Asset` — `asset_id`, `type` (office/dc/vendor), `geo`, `criticality`, `posture`
- `Person` — `person_id`, `role`, `sensitivity_tier`, `public_profile`
- `Trip` / `ItineraryLeg` — `trip_id`, `person_id`, `purpose`, `mission_profile` / `leg_id`, `geo`, `arrive_at`, `depart_at`

**Direction side (PIR decomposition chain):**
- `Requirement` — `req_id`, `kind` (PIR/FFIR), `question`, `owner_id`, `priority`, `geo_scope`, `expires_at`, `status`
- `SIR` — `sir_id`, `req_id`, `question`, `dimensions[]`, `status`
- `Indicator` — `indicator_id`, `sir_id`, `description`, `observable_pattern`, `volatility`
- `CollectionTasking` — `tasking_id`, `indicator_id`, `source_id`, `frequency`, `last_collected_at`, `status`

**Analysis side:**
- `Assessment` — `assessment_id`, `subject_type`, `subject_id`, `framework`, `inherent_score`, `residual_score`, `analytic_confidence`, `status` (draft/in_review/approved/superseded), `author`, `reviewer_id`, `approved_at`
- `DimensionScore` — `assessment_id`, `dimension`, `base`, `delta`, `value`, `analytic_confidence`, `weight`
- `Evidence` — `dimension_score_id`, `event_id`, `contribution`, `quote`, `retrieved_at`

#### [NEW] `packages/shared/src/shared/ts_models.py`
Move existing ContentItem, ModerationDecision, SeverityTier, etc. here so Coptoc tests keep passing.

#### [MODIFY] [db_models.py](file:///Users/h4yd3n/Apps/TOC/packages/shared/src/shared/db_models.py)
Add SQLAlchemy ORM models for all 12 entities. Keep existing LedgerEventRow, ModerationDecisionRow, ContentStateRow.

#### [MODIFY] [constants.py](file:///Users/h4yd3n/Apps/TOC/packages/shared/src/shared/constants.py)
Add:
- `RISK_DIMENSIONS` — the 8 dimensions from §6.2 with half-lives and default proximity sigmas
- `ADMIRALTY_RELIABILITY_WEIGHTS` — A=1.0, B=0.8, C=0.6, D=0.3, E=0.1, F=0.5 (unknown ≠ unreliable)
- `ADMIRALTY_CREDIBILITY_WEIGHTS` — 1=1.0, 2=0.8, 3=0.6, 4=0.3, 5=0.1, 6=0.5
- `ICD203_TERMS` — the 7 estimative probability terms with their numeric ranges
- `SCORE_BANDS` — LOW/GUARDED/MODERATE/HIGH/SEVERE thresholds from §6.7

---

## Phase 2: OSINT Collection Layer

> PRD §4.1.2 — Pluggable connectors with a standard interface. Source configuration by administrators.

### Connector Architecture

#### [MODIFY] [base.py](file:///Users/h4yd3n/Apps/TOC/apps/sigtoc/src/sigtoc/connectors/base.py)
Redesign the base connector interface:

```python
class BaseConnector(ABC):
    source: Source  # includes discipline, reliability rating
    
    @abstractmethod
    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None) -> List[Signal]:
        """Collect raw signals, returning immutable Signal objects."""
    
    @abstractmethod
    def health_check(self) -> ConnectorHealth:
        """Return connector status for synchronization matrix."""
```

All connectors return `Signal` objects — the atom of the system. Signals are immutable, append-only.

---

### Connector 1: US State Department Travel Advisories

#### [NEW] `apps/sigtoc/src/sigtoc/connectors/state_dept.py`

**API Details:**
- Endpoint: `https://cadataapi.state.gov/api/TravelAdvisories` (all countries) or `https://cadataapi.state.gov/api/TravelAdvisories/{country_code}.json`
- Auth: None
- Format: JSON
- Fields: Country code, advisory level (1-4), risk indicators (C=Crime, T=Terrorism, U=Unrest), advisory text, date updated

**Implementation:**
- Fetches advisory for a specific country code
- Maps advisory level to base scores: Level 1→0.5, Level 2→1.5, Level 3→3.0, Level 4→4.5 (per §6.3)
- Parses risk indicator letters into dimension mappings
- Extracts country-specific safety sections (Crime, Terrorism, Civil Unrest, etc.) as signal text
- Source reliability: A2 (government, structured)
- Collection frequency: Daily

---

### Connector 2: GDELT

#### [NEW] `apps/sigtoc/src/sigtoc/connectors/gdelt.py`

**API Details:**
- Doc API: `http://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&format=json`
- Events via `gdelt` PyPI package (wraps CSV downloads)
- Fields: CAMEO event codes, ActionGeo_Lat/Lon, GoldsteinScale (severity), NumMentions, Actor1Name
- Auth: None
- Rate limits: Light querying only for REST API

**Implementation:**
- Uses `gdelt` Python package for structured event queries
- Filters by `ActionGeo_CountryCode` for the target country
- Maps CAMEO event codes to risk dimensions (14x = Protests → Civil Unrest, 18x = Violence → Terrorism/Crime)
- Uses GoldsteinScale as event severity input
- Deduplicates by `origin_key` (GDELT `SOURCEURL` field) — forty outlets republishing one wire = one signal
- Source reliability: B3 (aggregated, noisy — needs corroboration)
- Collection frequency: Daily (15-minute updates available but unnecessary for travel assessment cadence)

---

### Connector 3: GDACS

#### [NEW] `apps/sigtoc/src/sigtoc/connectors/gdacs_connector.py`

**API Details:**
- API: `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH`
- RSS: `https://www.gdacs.org/xml/rss.xml` (updates every 6 minutes)
- PyPI: `gdacs-api` package
- Fields: eventid, eventtype (EQ/FL/TC/VO/DR), alertlevel (Green/Orange/Red), lat/lon, severitydata
- Auth: None

**Implementation:**
- Uses `gdacs-api` package for structured queries
- Filters events by proximity to itinerary legs (using §6.3 `proximity_e` formula)
- Maps alert levels to severity: Green→0.2, Orange→0.5, Red→0.9
- Maps event types to Natural Hazards dimension
- Source reliability: A1 (UN-operated, authoritative)
- Collection frequency: Every 6 hours

---

### Connector 4: WHO/CDC Health Notices

#### [NEW] `apps/sigtoc/src/sigtoc/connectors/health_notices.py`

**API Details:**
- CDC: `https://wwwnc.cdc.gov/travel/notices` (HTML scraping required)
- WHO: `https://www.who.int/emergencies/disease-outbreak-news` (HTML scraping)
- No structured JSON API available
- Fields: Notice level (1-3 for CDC), disease name, country/region, date

**Implementation:**
- Scrapes CDC travel notices page with `httpx` + `BeautifulSoup`
- Extracts notice level, disease, affected countries
- Maps CDC levels to severity: Level 1 (Watch)→0.3, Level 2 (Alert)→0.6, Level 3 (Warning)→0.9
- Falls back to cached data if scraping fails (graceful degradation)
- Source reliability: A1 (authoritative health agencies)
- Collection frequency: Daily

---

### Collection Manager

#### [NEW] `apps/sigtoc/src/sigtoc/collection/manager.py`
Orchestrates the synchronization matrix from §4.1.3:
- Takes a set of `CollectionTasking` records
- Runs the appropriate connector for each tasking
- Updates `last_collected_at` and `status` (CURRENT/DUE/OVERDUE/GAP)
- Stores collected `Signal` objects to database
- Reports collection gaps for the refuse-to-score chain

---

## Phase 3: Scoring Engine

> PRD §6 — Derived, never asserted. The AI does not decide a risk score.

#### [NEW] `apps/sigtoc/src/sigtoc/scoring/dimension_scorer.py`

Implements the §6.3 dimension scoring formula:

```
d_i = clamp( base_i + delta_i , 0 , 5 )
delta_i = 3.0 * tanh( sum( sev_e * recency_e * proximity_e * rating_e ) ) - 1.0
```

- `recency_e = 0.5 ^ (age_days / half_life_i)` — per-dimension half-life from §6.2
- `proximity_e = exp( -(dist_km^2) / (2 * sigma_i^2) )` — dimension-specific sigma
- `rating_e` = geometric mean of source reliability weight and information credibility weight (§6.5)

Takes as input: a list of `Evidence`-linked `Event` objects and the itinerary `geo`. Returns a `DimensionScore` with `base`, `delta`, `value`, and computed `analytic_confidence`.

#### [NEW] `apps/sigtoc/src/sigtoc/scoring/composite_scorer.py`

Implements §6.4:
- `inherent = sum(w_i * d_i) / sum(w_i)` — mission-weighted mean
- `residual = max(inherent * product(1 - credit_j), 0.4 * inherent)` — mitigation credits
- Maps to score band (LOW/GUARDED/MODERATE/HIGH/SEVERE) per §6.7

#### [NEW] `apps/sigtoc/src/sigtoc/scoring/confidence.py`

Implements §6.5 analytic confidence computation:
- Counts independent sources (collapsed by `origin_key`)
- Checks best Admiralty rating among sources
- Checks for unresolved contradictions
- Checks evidence staleness against half-life
- Returns HIGH/MODERATE/LOW/INSUFFICIENT per §6.5 criteria

#### [NEW] `apps/sigtoc/src/sigtoc/scoring/refuse_to_score.py`

Implements §6.6:
- Checks which dimensions have INSUFFICIENT confidence
- Sums their mission weights
- If >20% of total weight is INSUFFICIENT → refuse to emit overall score
- Returns the collection gap message identifying exactly what's missing

---

## Phase 4: AI Analysis Layer

> PRD §4.1.8 — The model extracts and drafts. It does not judge or publish.

#### [NEW] `apps/sigtoc/src/sigtoc/analysis/event_extractor.py`

Uses Claude to extract structured `Event` objects from raw `Signal` text:
- Input: `Signal.raw_text` (e.g., a news article about protests in Riyadh)
- Output: Structured `Event` with event_type, severity (from fixed rubric), geo, occurred_at
- The model classifies events into the §6.2 dimension taxonomy
- The model does NOT assign severity scores — it selects from a fixed rubric per event type (code enforces the mapping)

#### [NEW] `apps/sigtoc/src/sigtoc/analysis/assessment_drafter.py`

Uses Claude to draft BLUF-first assessments per §4.1.7:
- Input: Scored dimensions, evidence chains, trip details, selected framework (METT-TC / PMESII-PT)
- Output: Draft assessment text in BLUF-first structure
- The model selects estimative probability terms ONLY from the 7 ICD 203 terms (code attaches numeric bands)
- The model does NOT assign source reliability or grade its own confidence
- Assessment status = `draft` (human must move to `in_review` → `approved`)

#### [NEW] `apps/sigtoc/src/sigtoc/analysis/pir_decomposer.py`

Uses Claude to propose SIR decompositions when a PIR is created:
- Input: PIR question text, available sources, target geo
- Output: Proposed SIRs with indicator suggestions and dimension mappings
- Human reviews and approves the decomposition before collection begins

---

## Phase 5: Output Rendering & CLI

> PRD §4.1.7 — BLUF first, evidence second, gaps last.

#### [NEW] `apps/sigtoc/src/sigtoc/output/assessment_renderer.py`

Renders assessments in the BLUF-first format from §4.1.7:
1. BLUF (1-3 sentences, score band, recommendation)
2. Key Judgments (ICD 203 terms with numeric bands)
3. Dimension Detail (per-dimension scores with evidence citations)
4. Mitigations & Residual Risk
5. Collection Gaps

Supports both rich terminal output (via `rich` library) and markdown export.

#### [NEW] `apps/sigtoc/src/sigtoc/output/intsum_renderer.py`

Renders the Daily Intelligence Summary in the fixed INTSUM format from §4.1.7.

#### [NEW] `apps/sigtoc/src/sigtoc/cli.py`

CLI interface (using `click` or `typer`):

```bash
# Create a trip and auto-generate PIR
sigtoc trip create --traveler "CEO" --destination "Riyadh, Saudi Arabia" \
  --arrive 2026-10-01 --depart 2026-10-04 --purpose "Board meeting with Aramco"

# Run collection against all Tier 1 sources
sigtoc collect --trip TRIP-001

# View synchronization matrix status
sigtoc matrix --trip TRIP-001

# Generate travel risk assessment
sigtoc assess --trip TRIP-001 --framework mett-tc

# Review and approve (analyst workflow)
sigtoc review --assessment ASMT-001
sigtoc approve --assessment ASMT-001 --reviewer "analyst@company.com"

# View assessment
sigtoc report --assessment ASMT-001 --format rich

# Generate daily INTSUM
sigtoc intsum --date today
```

---

## Phase 6: Integration & Verification

#### [MODIFY] Tests

**New test files:**
- `tests/sigtoc/test_connectors.py` — Test each connector with mock responses (no live API calls in CI)
- `tests/sigtoc/test_scoring.py` — Test dimension scoring formula, composite scoring, refuse-to-score
- `tests/sigtoc/test_confidence.py` — Test Admiralty rating computation, ICD 203 confidence levels
- `tests/sigtoc/test_analysis.py` — Test event extraction and assessment drafting (mocked Claude)
- `tests/sigtoc/test_pir_decomposition.py` — Test PIR → SIR → Indicator chain
- `tests/integration/test_travel_risk_assessment.py` — End-to-end: create trip → collect → score → assess → refuse-to-score on insufficient dimensions

**Key end-to-end test (the demo):**
```python
def test_riyadh_travel_risk_assessment():
    """
    The killer demo: 'Our CEO needs to travel to Riyadh next month.'
    
    1. Create trip (Riyadh, 3-day, board meeting)
    2. System generates PIR and decomposes into SIRs
    3. Collect from State Dept (advisory level 2), GDELT (recent events),
       GDACS (no active disasters), CDC (no active health notices)
    4. Score 8 dimensions — expect:
       - Civil Unrest: LOW (stable monarchy)
       - Terrorism: LOW-MODERATE (Houthi activity peripheral)
       - Crime: LOW-MODERATE
       - Espionage: INSUFFICIENT (State Dept mentions surveillance but
         no dedicated espionage collection → refuse-to-score bridge)
       - Health: LOW
       - Natural Hazards: LOW (no active events)
       - Legal: MODERATE (strict local laws)
       - Infrastructure: scored from State Dept baseline
    5. Refuse-to-score fires if Espionage + Legal carry >20% weight
       OR produces partial assessment with gaps clearly stated
    6. Assessment renders in BLUF-first format
    7. All transitions logged to hash-chained ledger
    """
```

**Preserving existing tests:**
- All 21 existing Coptoc tests must still pass
- Existing Sigtoc tests will be replaced since the internals are reworked

### Verification Commands

```bash
# All tests (old + new)
make test

# Just the new Sigtoc intelligence engine tests
make test-sigtoc

# Live demo (requires ANTHROPIC_API_KEY for Claude analysis)
export ANTHROPIC_API_KEY=<your key>
sigtoc trip create --traveler "CEO" --destination "Riyadh, Saudi Arabia" \
  --arrive 2026-10-01 --depart 2026-10-04 --purpose "Board meeting"
sigtoc collect --trip TRIP-001
sigtoc assess --trip TRIP-001 --framework mett-tc
sigtoc report --assessment ASMT-001 --format rich
```

---

## Dependencies to Install

```bash
pip install gdelt          # GDELT data access
pip install gdacs-api      # GDACS disaster alerts
pip install beautifulsoup4 # WHO/CDC scraping
pip install typer[all]     # CLI framework
pip install geopy          # Geocoding and distance calculations
```

---

## What's NOT in This Plan (Phase 2+ per PRD §8)

- COP Dashboard / Blue Force Tracker map (web UI)
- Alerting tiers (FLASH/PRIORITY/ROUTINE)
- Incident management workflows
- Content moderation integration
- ACLED, CISA, News RSS connectors (Tier 2 sources)
- Paid premium connectors (Tier 3)
- Mobile app
- RBAC / access control
