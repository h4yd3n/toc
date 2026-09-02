import math
from datetime import datetime, timezone, timedelta
from shared.models import GeoPoint, DimensionScore, AnalyticConfidence
from sigtoc.scoring import (
    score_dimension,
    ScoredEvent,
    compute_composite,
    compute_analytic_confidence,
    check_refuse_to_score,
    admiralty_rating,
    haversine_km
)

def test_dimension_score_civil_unrest():
    ref_time = datetime.now(timezone.utc)
    ref_geo = GeoPoint(lat=40.7128, lon=-74.0060) # NYC

    # Recent protest, close (NYC)
    e1 = ScoredEvent(
        event_id="1", severity=0.8, geo=GeoPoint(lat=40.75, lon=-73.98),
        occurred_at=ref_time - timedelta(days=2),
        source_reliability="B", info_credibility=2, origin_key="src1"
    )
    # Old protest, close
    e2 = ScoredEvent(
        event_id="2", severity=0.8, geo=GeoPoint(lat=40.75, lon=-73.98),
        occurred_at=ref_time - timedelta(days=120),
        source_reliability="B", info_credibility=2, origin_key="src2"
    )
    # Recent protest, distant (LA)
    e3 = ScoredEvent(
        event_id="3", severity=0.8, geo=GeoPoint(lat=34.0522, lon=-118.2437),
        occurred_at=ref_time - timedelta(days=2),
        source_reliability="B", info_credibility=2, origin_key="src3"
    )

    base = 2.0
    # e1 alone
    score1 = score_dimension("civil_unrest", base, [e1], ref_geo, ref_time)
    # e2 alone
    score2 = score_dimension("civil_unrest", base, [e2], ref_geo, ref_time)
    # e3 alone
    score3 = score_dimension("civil_unrest", base, [e3], ref_geo, ref_time)

    # e1 should have a much bigger impact (delta) than e2 (due to recency) and e3 (due to proximity)
    assert score1.delta > score2.delta
    assert score1.delta > score3.delta
    # Delta of e3 should be very small/negative because it's far away
    
def test_dimension_score_with_no_events():
    ref_time = datetime.now(timezone.utc)
    ref_geo = GeoPoint(lat=0, lon=0)
    
    score = score_dimension("civil_unrest", 2.0, [], ref_geo, ref_time)
    # No events sum=0, 3*tanh(0) - 1.0 = -1.0
    # So delta is -1.0, value is 1.0
    assert score.delta == -1.0
    assert score.value == 1.0

def test_composite_score_with_mitigations():
    ds1 = DimensionScore(assessment_id="1", dimension="d1", base=0, delta=0, value=4.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)
    ds2 = DimensionScore(assessment_id="1", dimension="d2", base=0, delta=0, value=4.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)
    ds3 = DimensionScore(assessment_id="1", dimension="d3", base=0, delta=0, value=4.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)
    
    inherent, residual, band, rec = compute_composite([ds1, ds2, ds3], ["executive_protection"])
    
    # Inherent = 4.0
    assert inherent == 4.0
    # MITIGATION_CREDITS['executive_protection'] = 0.30 -> multiplier = (1 - 0.30) = 0.70
    # residual = max(4.0 * 0.70, 0.4 * 4.0) = max(2.8, 1.6) = 2.8
    assert residual < inherent
    assert residual >= 0.4 * inherent
    assert math.isclose(residual, 2.8)

def test_score_band_mapping():
    assert compute_composite([DimensionScore(assessment_id="1", dimension="d", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)])[2] == "LOW"
    assert compute_composite([DimensionScore(assessment_id="1", dimension="d", base=0, delta=0, value=2.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)])[2] == "GUARDED"
    assert compute_composite([DimensionScore(assessment_id="1", dimension="d", base=0, delta=0, value=3.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)])[2] == "MODERATE"
    assert compute_composite([DimensionScore(assessment_id="1", dimension="d", base=0, delta=0, value=4.0, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)])[2] == "HIGH"
    assert compute_composite([DimensionScore(assessment_id="1", dimension="d", base=0, delta=0, value=4.5, analytic_confidence=AnalyticConfidence.HIGH, weight=1.0)])[2] == "SEVERE"

def test_confidence_high():
    ref_time = datetime.now(timezone.utc)
    e1 = ScoredEvent(event_id="1", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="A", info_credibility=1, origin_key="s1")
    e2 = ScoredEvent(event_id="2", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="B", info_credibility=2, origin_key="s2")
    e3 = ScoredEvent(event_id="3", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="C", info_credibility=3, origin_key="s3")
    assert compute_analytic_confidence([e1, e2, e3], 30, ref_time) == AnalyticConfidence.HIGH

def test_confidence_moderate():
    ref_time = datetime.now(timezone.utc)
    e1 = ScoredEvent(event_id="1", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="C", info_credibility=3, origin_key="s1")
    e2 = ScoredEvent(event_id="2", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="D", info_credibility=4, origin_key="s2")
    assert compute_analytic_confidence([e1, e2], 30, ref_time) == AnalyticConfidence.MODERATE

def test_confidence_low():
    ref_time = datetime.now(timezone.utc)
    e1 = ScoredEvent(event_id="1", severity=0.5, geo=None, occurred_at=ref_time, source_reliability="A", info_credibility=1, origin_key="s1")
    assert compute_analytic_confidence([e1], 30, ref_time) == AnalyticConfidence.LOW

def test_confidence_insufficient():
    assert compute_analytic_confidence([], 30, datetime.now(timezone.utc)) == AnalyticConfidence.INSUFFICIENT

def test_refuse_to_score_fires():
    ds1 = DimensionScore(assessment_id="1", dimension="espionage", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.INSUFFICIENT, weight=0.15)
    ds2 = DimensionScore(assessment_id="1", dimension="legal_risk", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.INSUFFICIENT, weight=0.10)
    ds3 = DimensionScore(assessment_id="1", dimension="civil_unrest", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.HIGH, weight=0.75)
    
    msg = check_refuse_to_score([ds1, ds2, ds3])
    assert msg is not None
    assert "Espionage" in msg
    assert "Legal Risk" in msg
    assert "25%" in msg

def test_refuse_to_score_passes():
    ds1 = DimensionScore(assessment_id="1", dimension="legal_risk", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.INSUFFICIENT, weight=0.15)
    ds2 = DimensionScore(assessment_id="1", dimension="civil_unrest", base=0, delta=0, value=1.0, analytic_confidence=AnalyticConfidence.HIGH, weight=0.85)
    
    msg = check_refuse_to_score([ds1, ds2])
    assert msg is None

def test_admiralty_rating_geometric_mean():
    assert math.isclose(admiralty_rating('A', 1), 1.0)
    assert math.isclose(admiralty_rating('B', 3), math.sqrt(0.8 * 0.6))
    assert math.isclose(admiralty_rating('E', 6), math.sqrt(0.1 * 0.5))
    assert math.isclose(admiralty_rating('F', 6), 0.5)

def test_haversine_distance():
    # Riyadh: 24.7136, 46.6753
    # Dubai: 25.2048, 55.2708
    dist = haversine_km(24.7136, 46.6753, 25.2048, 55.2708)
    assert 860 <= dist <= 880
