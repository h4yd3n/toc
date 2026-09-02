import pytest
from datetime import datetime, timezone
from typer.testing import CliRunner

from sigtoc.output.assessment_renderer import AssessmentRenderer
from sigtoc.output.intsum_renderer import INTSUMRenderer
from shared.models import Assessment, Trip, DimensionScore, Evidence, GeoPoint, ItineraryLeg, AssessmentStatus, AnalyticConfidence
from sigtoc.cli import app, load_state, save_state
import os
import json

runner = CliRunner()

@pytest.fixture
def mock_trip():
    return Trip(
        trip_id="trip_123",
        person_id="CEO",
        purpose="Board meeting",
        legs=[ItineraryLeg(
            leg_id="leg_1",
            geo=GeoPoint(lat=24.7136, lon=46.6753, label="Riyadh"),
            arrive_at=datetime.now(timezone.utc),
            depart_at=datetime.now(timezone.utc)
        )]
    )

@pytest.fixture
def mock_assessment():
    return Assessment(
        assessment_id="asmt_123",
        subject_type="trip",
        subject_id="trip_123",
        inherent_score=75.5,
        analytic_confidence=AnalyticConfidence.MODERATE,
        status=AssessmentStatus.DRAFT,
        collection_gaps=["No ground truth from local assets"]
    )

@pytest.fixture
def mock_dimension_scores():
    return [
        DimensionScore(assessment_id="asmt_123", dimension="Mission", base=70, delta=5, value=75, analytic_confidence=AnalyticConfidence.HIGH)
    ]

@pytest.fixture
def mock_evidence():
    return [
        Evidence(dimension_score_id="asmt_123_Mission", event_id="evt_1", contribution=5.0, quote="High profile target detected")
    ]

def test_assessment_markdown(mock_trip, mock_assessment, mock_dimension_scores, mock_evidence):
    md = AssessmentRenderer.render_markdown(mock_assessment, mock_trip, mock_dimension_scores, mock_evidence)
    assert "TACTICAL ASSESSMENT: CEO" in md
    assert "BOTTOM LINE UP FRONT (BLUF)" in md
    assert "75.5" in md
    assert "KEY JUDGMENTS" in md
    assert "DIMENSION SCORES" in md
    assert "MISSION" in md
    assert "High profile target detected" in md
    assert "MITIGATIONS" in md
    assert "COLLECTION GAPS" in md
    assert "No ground truth from local assets" in md

def test_intsum_markdown():
    md = INTSUMRenderer.render_markdown(
        date_str="2026-10-01",
        bluf="Test BLUF",
        pir_statuses=[{"id": "PIR-01", "status": "ACTIVE"}],
        significant_signals=[{"source": "OSINT", "summary": "Alert", "credibility": 3}],
        score_changes=[{"entity": "HQ", "old": 40, "new": 50, "reason": "Intel"}],
        active_travel=[{"person": "CFO", "location": "London", "risk": "Low"}],
        collection_gaps=[{"description": "None"}]
    )
    
    assert "INTELLIGENCE SUMMARY (INTSUM) - 2026-10-01" in md
    assert "Test BLUF" in md
    assert "PIR-01**: ACTIVE" in md
    assert "OSINT**: Alert" in md
    assert "HQ: 40 -> 50" in md
    assert "CFO**: London" in md
    assert "None" in md

def test_cli_trip_create_and_list():
    if os.path.exists("sigtoc_state.json"):
        os.remove("sigtoc_state.json")
    
    result = runner.invoke(app, [
        "trip", "create", 
        "--traveler", "CEO", 
        "--destination", "Riyadh, Saudi Arabia", 
        "--lat", "24.7136", 
        "--lon", "46.6753", 
        "--arrive", "2026-10-01", 
        "--depart", "2026-10-04", 
        "--purpose", "Board meeting"
    ])
    assert result.exit_code == 0
    assert "Created trip" in result.stdout
    
    result = runner.invoke(app, ["trip", "list"])
    assert result.exit_code == 0
    assert "CEO to Riyadh, Saudi Arabia (Board meeting)" in result.stdout

def test_cli_flow():
    if os.path.exists("sigtoc_state.json"):
        os.remove("sigtoc_state.json")
        
    # Create trip
    runner.invoke(app, [
        "trip", "create", 
        "--traveler", "CEO", 
        "--destination", "Riyadh, Saudi Arabia", 
        "--lat", "24.7136", 
        "--lon", "46.6753", 
        "--arrive", "2026-10-01", 
        "--depart", "2026-10-04", 
        "--purpose", "Board meeting"
    ])
    
    state = load_state()
    trip_id = list(state["trips"].keys())[0]
    
    # Collect
    result = runner.invoke(app, ["collect", "--trip", trip_id])
    assert result.exit_code == 0
    assert "Collection complete" in result.stdout
    
    # Matrix
    result = runner.invoke(app, ["matrix", "--trip", trip_id])
    assert result.exit_code == 0
    assert "osint_api" in result.stdout
    
    # Assess
    result = runner.invoke(app, ["assess", "--trip", trip_id, "--framework", "mett-tc"])
    assert result.exit_code == 0
    assert "generated in DRAFT state" in result.stdout
    
    state = load_state()
    asmt_id = list(state["assessments"].keys())[0]
    
    # Approve
    result = runner.invoke(app, ["approve", "--assessment", asmt_id, "--reviewer", "analyst@company.com"])
    assert result.exit_code == 0
    assert "APPROVED by analyst@company.com" in result.stdout
    
    # Report markdown
    result = runner.invoke(app, ["report", "--assessment", asmt_id, "--format", "markdown"])
    assert result.exit_code == 0
    assert "TACTICAL ASSESSMENT" in result.stdout
    
    # Intsum
    result = runner.invoke(app, ["intsum", "--date", "today"])
    assert result.exit_code == 0
    assert "INTELLIGENCE SUMMARY (INTSUM) - today" in result.stdout
