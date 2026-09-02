import os
import pytest
from datetime import datetime, timezone
import uuid

from shared.models import (
    Signal, AdmiraltyCredibility, GeoPoint,
    Trip, Requirement, RequirementKind, DimensionScore, AnalyticConfidence, AssessmentStatus
)

from sigtoc.analysis import EventExtractor, AssessmentDrafter, PIRDecomposer

def test_event_extractor_heuristics():
    # Force heuristics by unsetting API key
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
        
    extractor = EventExtractor()
    signal = Signal(
        signal_id="sig-1",
        source_id="src-1",
        credibility=AdmiraltyCredibility.PROBABLY_TRUE,
        raw_text="A massive protest and riot broke out downtown.",
        content_hash="hash"
    )
    
    events = extractor.extract_events(signal)
    assert len(events) == 1
    scored_event = events[0]
    assert scored_event.event.event_type == "protest"
    assert "civil_unrest" in scored_event.affected_dimensions
    assert len(scored_event.key_quotes) > 0

def test_assessment_drafter_heuristics():
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
        
    drafter = AssessmentDrafter()
    trip = Trip(
        trip_id="trip-1",
        person_id="p-1",
        purpose="Executive visit"
    )
    
    dimension_scores = [
        DimensionScore(
            assessment_id="dummy",
            dimension="civil_unrest",
            base=2.0,
            delta=0.5,
            value=2.5,
            analytic_confidence=AnalyticConfidence.MODERATE
        )
    ]
    
    draft = drafter.draft_assessment(
        trip=trip,
        dimension_scores=dimension_scores,
        evidence=[],
        inherent_score=2.5,
        residual_score=2.0,
        band="GUARDED",
        recommendation="Proceed with caution",
        collection_gaps=["Local police response time"]
    )
    
    assert draft.assessment.status == AssessmentStatus.DRAFT
    assert "BLUF" in draft.bluf
    assert len(draft.key_judgments) > 0
    assert "Mission" in draft.framework_sections
    assert "collection gaps" in draft.collection_gaps_statement

def test_pir_decomposer_heuristics():
    if "ANTHROPIC_API_KEY" in os.environ:
        del os.environ["ANTHROPIC_API_KEY"]
        
    decomposer = PIRDecomposer()
    req = Requirement(
        req_id="req-1",
        kind=RequirementKind.PIR,
        question="Will protests disrupt the route?",
        owner_id="user-1"
    )
    
    result = decomposer.decompose(req, "Downtown Seattle")
    
    assert len(result.sirs) > 0
    assert len(result.indicators) > 0
    assert result.indicators[0].sir_id == result.sirs[0].sir_id
    assert "infrastructure" in result.sirs[1].dimensions or "terrorism" in result.sirs[0].dimensions
