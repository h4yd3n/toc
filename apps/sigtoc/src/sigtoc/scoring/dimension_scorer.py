import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from shared.models import GeoPoint, DimensionScore, AnalyticConfidence
from shared.constants import RISK_DIMENSIONS
from sigtoc.scoring.confidence import admiralty_rating, compute_analytic_confidence

@dataclass
class ScoredEvent:
    event_id: str
    severity: float  # 0-1
    geo: Optional[GeoPoint]
    occurred_at: Optional[datetime]
    source_reliability: str  # 'A'-'F'
    info_credibility: int    # 1-6
    quote: str = ''
    origin_key: Optional[str] = None

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def score_dimension(
    dimension: str,
    base: float,
    events: List[ScoredEvent],
    reference_geo: GeoPoint,
    reference_time: datetime,
    weight: float = 1.0,
) -> DimensionScore:
    dim_config = RISK_DIMENSIONS[dimension]
    half_life_days = dim_config['half_life_days']
    proximity_sigma_km = dim_config['proximity_sigma_km']
    
    total_val = 0.0
    for event in events:
        sev_e = event.severity
        
        # Recency
        if event.occurred_at:
            age_days = (reference_time - event.occurred_at).total_seconds() / 86400
            # cap at 0 so future events don't explode (or just use age_days)
            if age_days < 0:
                age_days = 0
            recency_e = 0.5 ** (age_days / half_life_days)
        else:
            recency_e = 1.0
            
        # Proximity
        if proximity_sigma_km is None or event.geo is None:
            proximity_e = 1.0
        else:
            dist_km = haversine_km(
                reference_geo.lat, reference_geo.lon,
                event.geo.lat, event.geo.lon
            )
            proximity_e = math.exp(-(dist_km**2) / (2 * proximity_sigma_km**2))
            
        # Rating
        rating_e = admiralty_rating(event.source_reliability, event.info_credibility)
        
        total_val += sev_e * recency_e * proximity_e * rating_e
        
    delta_i = 3.0 * math.tanh(total_val) - 1.0
    
    d_i = base + delta_i
    if d_i < 0.0:
        d_i = 0.0
    if d_i > 5.0:
        d_i = 5.0
        
    confidence = compute_analytic_confidence(events, half_life_days, reference_time)
    
    return DimensionScore(
        assessment_id="tmp", # Or however we want to initialize it
        dimension=dimension,
        base=base,
        delta=delta_i,
        value=d_i,
        analytic_confidence=confidence,
        weight=weight
    )
