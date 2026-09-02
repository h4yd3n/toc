import pytest
from datetime import datetime, timezone, timedelta
from shared.models import (
    Trip, ItineraryLeg, GeoPoint, Requirement, RequirementKind,
    RequirementStatus, AssessmentStatus, AdmiraltyReliability, AdmiraltyCredibility,
    Signal, Source, IntelDiscipline, DimensionScore, AnalyticConfidence
)
from shared.constants import (
    RISK_DIMENSIONS, ADMIRALTY_RELIABILITY_WEIGHTS, ADMIRALTY_CREDIBILITY_WEIGHTS
)
from sigtoc.analysis.pir_decomposer import PIRDecomposer
from sigtoc.analysis.event_extractor import EventExtractor
from sigtoc.analysis.assessment_drafter import AssessmentDrafter
from sigtoc.scoring.dimension_scorer import score_dimension, ScoredEvent
from sigtoc.scoring.composite_scorer import compute_composite
from sigtoc.scoring.refuse_to_score import check_refuse_to_score
from sigtoc.output.assessment_renderer import AssessmentRenderer
from coptoc.ledger.event_stream import ImmutableEventLedger


def test_end_to_end_riyadh_travel_risk_assessment():
    """
    End-to-end demonstration of the Directed Travel Risk Assessment:
    1. Security Director defines trip for CEO to Riyadh, Saudi Arabia.
    2. PIR is decomposed into SIRs, Indicators, and mapped to dimensions.
    3. Multi-source OSINT collection signals are processed and events extracted.
    4. Deterministic scoring computes dimension scores with Admiralty ratings & half-life decay.
    5. Demonstrates the Refuse-to-Score rule firing when mission-critical dimensions lack collection.
    6. Demonstrates complete BLUF-first METT-TC assessment generation when collection is satisfied.
    7. Demonstrates Analyst review, approval, and immutable ledger recording.
    """
    now = datetime.now(timezone.utc)
    ledger = ImmutableEventLedger()

    # Step 1: Define Trip
    riyadh_geo = GeoPoint(lat=24.7136, lon=46.6753, label="Riyadh, Saudi Arabia")
    trip = Trip(
        trip_id="TRIP-SA-2026-001",
        person_id="PERSON-CEO-01",
        purpose="Board meeting with energy partners & government leadership",
        mission_profile="executive_keynote",
        legs=[
            ItineraryLeg(
                leg_id="LEG-01",
                geo=riyadh_geo,
                arrive_at=now + timedelta(days=5),
                depart_at=now + timedelta(days=8)
            )
        ]
    )

    # Step 2: Create PIR and Decompose
    pir = Requirement(
        req_id="PIR-2026-SA-01",
        kind=RequirementKind.PIR,
        question="What are the active terrorism, civil unrest, and espionage risks to Western executive travelers in Riyadh over the next 30 days?",
        owner_id="DIR-SECURITY-01",
        priority=1,
        geo_scope=riyadh_geo,
        status=RequirementStatus.ACTIVE
    )

    decomposer = PIRDecomposer()
    decomposed = decomposer.decompose(pir, context="Executive board meeting in Riyadh, Saudi Arabia")
    assert len(decomposed.sirs) >= 3
    assert len(decomposed.indicators) >= 3

    # Step 3: Simulate OSINT Signals
    sig_state_dept = Signal(
        signal_id="SIG-SD-001",
        source_id="SRC-STATE-DEPT",
        credibility=AdmiraltyCredibility.PROBABLY_TRUE,
        raw_text="State Dept Travel Advisory Level 2: Exercise Increased Caution in Saudi Arabia due to the threat of missile and drone attacks and terrorism.",
        url="https://travel.state.gov/advisories/saudi_arabia",
        published_at=now - timedelta(days=3),
        collected_at=now,
        content_hash="hash_sd_001",
        origin_key="sd_sa_2026"
    )

    sig_gdelt = Signal(
        signal_id="SIG-GD-002",
        source_id="SRC-GDELT",
        credibility=AdmiraltyCredibility.POSSIBLY_TRUE,
        raw_text="Regional security report: Border skirmishes reported 650km southwest of Riyadh; metropolitan Riyadh remains calm with high internal security.",
        url="https://news.example.com/saudi-security-update",
        published_at=now - timedelta(days=1),
        collected_at=now,
        content_hash="hash_gd_002",
        origin_key="gdelt_sa_border_2026"
    )

    # Step 4: Extract Events from Signals
    extractor = EventExtractor()
    scored_events_sd = extractor.extract_events(sig_state_dept)
    scored_events_gd = extractor.extract_events(sig_gdelt)
    extracted_events = scored_events_sd + scored_events_gd
    assert len(extracted_events) >= 2

    # Step 5: Test Refuse-to-Score Rule
    incomplete_dimension_scores = []
    # Build civil unrest score
    incomplete_dimension_scores.append(score_dimension(
        dimension="civil_unrest",
        base=1.5,
        events=[
            ScoredEvent(
                event_id="EVT-CU-TEMP",
                severity=0.2,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=2),
                source_reliability="A",
                info_credibility=2,
                quote="Municipal stability maintained with no planned civil unrest."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.25
    ))
    # Build terrorism score
    incomplete_dimension_scores.append(score_dimension(
        dimension="terrorism",
        base=1.5,
        events=[
            ScoredEvent(
                event_id="EVT-T-TEMP",
                severity=0.4,
                geo=GeoPoint(lat=18.2164, lon=42.5053, label="Abha/Southern Border"),
                occurred_at=now - timedelta(days=1),
                source_reliability="B",
                info_credibility=2,
                quote="Air defense intercepted drone in southern province."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.30
    ))
    # Uncollected dimensions (Espionage, Violent Crime) -> INSUFFICIENT
    incomplete_dimension_scores.append(DimensionScore(
        assessment_id="ASMT-SA-TEMP",
        dimension="espionage",
        base=1.5,
        delta=0.0,
        value=1.5,
        analytic_confidence=AnalyticConfidence.INSUFFICIENT,
        weight=0.25  # 25% > 20% threshold
    ))
    incomplete_dimension_scores.append(DimensionScore(
        assessment_id="ASMT-SA-TEMP",
        dimension="violent_crime",
        base=1.0,
        delta=0.0,
        value=1.0,
        analytic_confidence=AnalyticConfidence.INSUFFICIENT,
        weight=0.20
    ))

    # Refuse-to-score must trigger on incomplete mission-critical intelligence
    gap_msg = check_refuse_to_score(incomplete_dimension_scores)
    assert gap_msg is not None
    assert "Assessment incomplete" in gap_msg
    assert "Espionage" in gap_msg or "Violent Crime" in gap_msg

    # Step 6: Full Assessment Generation with Satisfied Collection
    complete_dimension_scores = []
    
    # Civil unrest (low risk in Riyadh)
    complete_dimension_scores.append(score_dimension(
        dimension="civil_unrest",
        base=1.5,
        events=[
            ScoredEvent(
                event_id="EVT-CU-1",
                severity=0.2,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=2),
                source_reliability="A",
                info_credibility=2,
                quote="Municipal stability maintained with no planned civil unrest."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.15
    ))

    # Terrorism (moderate baseline due to regional factors)
    complete_dimension_scores.append(score_dimension(
        dimension="terrorism",
        base=1.5,
        events=[
            ScoredEvent(
                event_id="EVT-T-1",
                severity=0.4,
                geo=GeoPoint(lat=18.2164, lon=42.5053, label="Abha/Southern Border"), # 600+ km away
                occurred_at=now - timedelta(days=1),
                source_reliability="B",
                info_credibility=2,
                quote="Air defense intercepted drone in southern province; no impact on capital."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.30
    ))

    # Espionage (loaner device protocol required)
    complete_dimension_scores.append(score_dimension(
        dimension="espionage",
        base=2.0,
        events=[
            ScoredEvent(
                event_id="EVT-ESP-1",
                severity=0.5,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=10),
                source_reliability="A",
                info_credibility=2,
                quote="State surveillance capabilities active for commercial delegations."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.20
    ))

    # Violent crime
    complete_dimension_scores.append(score_dimension(
        dimension="violent_crime",
        base=1.0,
        events=[
            ScoredEvent(
                event_id="EVT-CRIME-1",
                severity=0.1,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=5),
                source_reliability="A",
                info_credibility=1,
                quote="Violent crime rates in diplomatic and business districts remain exceptionally low."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.15
    ))

    # Natural hazards / health
    complete_dimension_scores.append(score_dimension(
        dimension="natural_hazards",
        base=0.5,
        events=[
            ScoredEvent(
                event_id="EVT-NAT-1",
                severity=0.1,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=1),
                source_reliability="A",
                info_credibility=1,
                quote="Weather calm; no sandstorms or extreme events forecast."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.10
    ))

    complete_dimension_scores.append(score_dimension(
        dimension="health_medical",
        base=0.5,
        events=[
            ScoredEvent(
                event_id="EVT-MED-1",
                severity=0.1,
                geo=riyadh_geo,
                occurred_at=now - timedelta(days=1),
                source_reliability="A",
                info_credibility=1,
                quote="Standard precautions; Tier 1 medical centers operational."
            )
        ],
        reference_geo=riyadh_geo,
        reference_time=now,
        weight=0.10
    ))

    # No refuse-to-score now
    assert check_refuse_to_score(complete_dimension_scores) is None

    # Step 7: Calculate Inherent & Residual Scores with Mitigation Credits
    mitigations = ["executive_protection_detail", "clean_device_protocol", "vetted_transport"]
    inherent, residual, band, rec = compute_composite(
        complete_dimension_scores,
        mitigations=mitigations
    )

    assert 0.0 < residual < inherent
    assert band in ["LOW", "GUARDED", "MODERATE", "HIGH", "SEVERE"]
    assert "Approve" in rec

    # Step 8: AI Drafter builds METT-TC Assessment
    drafter = AssessmentDrafter()
    drafted = drafter.draft_assessment(
        trip=trip,
        dimension_scores=complete_dimension_scores,
        evidence=[],
        inherent_score=inherent,
        residual_score=residual,
        band=band,
        recommendation=rec,
        collection_gaps=[],
        framework="mett-tc"
    )

    assessment = drafted.assessment
    assert assessment.status == AssessmentStatus.DRAFT
    assert assessment.author == "ai"

    # Step 9: Render Assessment in BLUF-First Markdown
    renderer = AssessmentRenderer()
    md_output = renderer.render_markdown(
        assessment=assessment,
        trip=trip,
        dimension_scores=complete_dimension_scores,
        evidence=[]
    )

    assert "BOTTOM LINE UP FRONT (BLUF)" in md_output
    assert "KEY JUDGMENTS" in md_output
    assert "METT-TC" in md_output
    assert "DIMENSION SCORES" in md_output

    # Step 10: Analyst Review & Approval + Hash-Chained Ledger
    assessment.status = AssessmentStatus.APPROVED
    assessment.reviewer_id = "ANALYST-LEAD-01"
    assessment.approved_at = datetime.now(timezone.utc)

    ledger_event = ledger.append_event(
        content_id=trip.trip_id,
        event_type="travel_assessment_approved",
        actor_type="human_analyst",
        actor_id=assessment.reviewer_id,
        reason=f"Approved with residual score {residual:.2f} ({band}) under METT-TC framework.",
        metadata={
            "assessment_id": assessment.assessment_id,
            "inherent_score": inherent,
            "residual_score": residual,
            "band": band,
            "mitigations": mitigations
        }
    )

    assert ledger_event.prev_hash is None or len(ledger_event.prev_hash) == 64
    assert ledger.verify_chain_integrity(trip.trip_id) is True
