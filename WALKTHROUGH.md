# Walkthrough: TOC MVP — Sigtoc Intelligence Engine

We have implemented the full **TOC MVP** according to the [Product Requirements Document (PRD.md)](file:///Users/h4yd3n/Apps/TOC/PRD.md) and [Implementation Plan](file:///Users/h4yd3n/Apps/TOC/IMPLEMENTATION_PLAN.md), focused on the **Directed Travel Risk Assessment** intelligence workflow.

---

## 1. Accomplished Architecture & Implementation

```
                           DIRECTION (PIR Decomposition)
                           ─────────────────────────────
     Requirement (PIR/FFIR) ──▶ SIRs ──▶ Indicators ──▶ CollectionTasking (Sync Matrix)
                                                            │
                                                            │
            ┌───────────────────────────────────────────────┴───────────────────────┐
            ▼                                                                       ▼
    TIER 1 OSINT CONNECTORS                                            AI EXTRACTION & SCORING
    ───────────────────────                                            ───────────────────────
    • State Dept (Travel Advisories JSON API)                         • EventExtractor (Dual-mode)
    • GDELT 2.0 (Doc API / Global Events)                             • DimensionScorer (PRD §6.3 equation)
    • GDACS (Disaster alerts RSS / Geo)                               • CompositeScorer (Inherent/Residual)
    • CDC / WHO (Travel Health Notices Scraper)                       • Confidence & Admiralty Rating
                                                                      • Refuse-to-Score Rule (PRD §6.6)
                                                                                    │
                                                                                    ▼
                                                                       AI ASSESSMENT DRAFTER
                                                                       ─────────────────────
                                                                      • METT-TC / PMESII-PT Drafts
                                                                      • Strict ICD 203 Judgments
                                                                      • BLUF-First Renderers & CLI
                                                                      • Hash-Chained Immutable Ledger
```

### 1. Data Model (`packages/shared/src/shared/models.py`, `constants.py`)
- **12 Primary Entities**: `Source`, `Signal`, `Event`, `Asset`, `Person`, `Trip`, `ItineraryLeg`, `Requirement`, `SIR`, `Indicator`, `CollectionTasking`, `Assessment`, `DimensionScore`, and `Evidence`.
- **Standards & Metrics**:
  - Admiralty Rating Scale ($A\text{--}F \times 1\text{--}6$) with geometric mean calculation.
  - ICD 203 Estimative Language scale (7 fixed numeric probability bands).
  - 8 Risk Dimensions with half-lives and proximity sigmas ($\sigma_i$).
  - 5 Score Bands (`LOW`, `GUARDED`, `MODERATE`, `HIGH`, `SEVERE`).
  - PRD §6.4 Mitigation credits (`executive_protection_detail`, `vetted_transport`, `clean_device_protocol`, etc.).

### 2. OSINT Collection Layer (`apps/sigtoc/src/sigtoc/connectors/`, `collection/`)
- `BaseConnector`: Async base with `GeoScope`, `TimeWindow`, and `ConnectorHealth`.
- `StateDeptConnector`: Consular JSON API integration.
- `GDELTConnector`: Doc API event aggregator with URL-based `origin_key` deduplication.
- `GDACSConnector`: UN disaster alert parser with exact GeoPoint coordinates and severity mapping.
- `HealthNoticesConnector`: CDC/WHO scraper for outbreak and epidemic tracking.
- `CollectionManager`: Synchronization matrix orchestration tracking tasking status (`CURRENT`, `DUE`, `OVERDUE`, `GAP`).

### 3. Threat Scoring Engine (`apps/sigtoc/src/sigtoc/scoring/`)
- `dimension_scorer.py`: Implements $d_i = \text{clamp}(\text{base}_i + \delta_i, 0, 5)$ with:
  - $\text{recency}_e = 0.5^{(\text{age\_days} / \text{half\_life}_i)}$
  - $\text{proximity}_e = \exp\left(-\frac{\text{dist\_km}^2}{2\sigma_i^2}\right)$ via Haversine spherical distance
  - $\text{rating}_e = \sqrt{\text{reliability\_weight} \times \text{credibility\_weight}}$
- `composite_scorer.py`: Computes mission-weighted inherent score and applies mitigation credits with a hard $0.4 \times \text{Inherent}$ floor.
- `confidence.py`: Computes ICD 203 analytic confidence (`HIGH`, `MODERATE`, `LOW`, `INSUFFICIENT`) based on source independence and corroborated track records.
- `refuse_to_score.py`: Implements PRD §6.6 — refuses to emit a composite score if uncollected/`INSUFFICIENT` dimensions exceed 20% of mission weight.

### 4. AI Analysis & Output (`apps/sigtoc/src/sigtoc/analysis/`, `output/`, `cli.py`)
- `PIRDecomposer`: Decomposes PIRs into 3-5 SIRs and observable indicators with dimension tags.
- `EventExtractor`: Extracts structured events and quotes from raw signals.
- `AssessmentDrafter`: Synthesizes BLUF-first METT-TC / PMESII-PT draft assessments in `AssessmentStatus.DRAFT`.
- `AssessmentRenderer` & `INTSUMRenderer`: Outputs formatted reports in Markdown and Rich tactical terminal consoles.
- `sigtoc` CLI: Typer commands for `trip`, `collect`, `matrix`, `assess`, `approve`, `report`, `intsum`.

---

## 2. Test Verification

All **47 tests** across both Coptoc and Sigtoc pass cleanly:

```bash
PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src .venv/bin/pytest tests/ -v
```

### Key Test Suites:
- `tests/integration/test_travel_risk_assessment.py`: Comprehensive end-to-end Riyadh CEO board meeting trip test covering PIR decomposition, multi-source signal processing, Refuse-to-Score verification on missing collection, complete METT-TC BLUF assessment, and analyst approval recording to the hash-chained ledger.
- `tests/sigtoc/test_scoring.py`: 12 mathematical verification tests for dimension scoring, half-life decay, haversine proximity decay, mitigation credit floors, and refuse-to-score thresholds.
- `tests/sigtoc/test_connectors.py`: 6 connector and collection manager tests with mocked network responses.
- `tests/sigtoc/test_analysis.py`: Dual-mode PIR decomposition, event extraction, and assessment drafting tests.
- `tests/sigtoc/test_output_and_cli.py`: Typer CLI command runner and renderer verification.
- `tests/coptoc/*`: All 21 original Coptoc moderation engine & compiler tests remain 100% green.

---

## 3. Trying the CLI

You can run the `sigtoc` CLI directly:

```bash
# 1. Create a trip
PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src .venv/bin/python -m sigtoc.cli trip create \
  --traveler "CEO" \
  --destination "Riyadh, Saudi Arabia" \
  --lat 24.7136 --lon 46.6753 \
  --arrive "2026-10-01" --depart "2026-10-04" \
  --purpose "Board meeting with energy partners"

# 2. View synchronization matrix
PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src .venv/bin/python -m sigtoc.cli matrix --trip <trip_id>

# 3. Generate travel assessment
PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src .venv/bin/python -m sigtoc.cli assess --trip <trip_id> --framework mett-tc

# 4. View formatted tactical report
PYTHONPATH=packages/shared/src:apps/coptoc/src:apps/sigtoc/src .venv/bin/python -m sigtoc.cli report --assessment <asmt_id> --format rich
```
