import math
from typing import List
from datetime import datetime, timezone
from shared.models import AnalyticConfidence
from shared.constants import ADMIRALTY_RELIABILITY_WEIGHTS, ADMIRALTY_CREDIBILITY_WEIGHTS

def admiralty_rating(reliability: str, credibility: int) -> float:
    r = ADMIRALTY_RELIABILITY_WEIGHTS.get(reliability, 0.5)
    c = ADMIRALTY_CREDIBILITY_WEIGHTS.get(credibility, 0.5)
    return math.sqrt(r * c)

def compute_analytic_confidence(
    events: List[Any],
    half_life_days: float,
    reference_time: datetime,
) -> AnalyticConfidence:
    if not events:
        return AnalyticConfidence.INSUFFICIENT
    
    independent_sources = set()
    b2_or_better_count = 0
    c3_or_better_count = 0
    
    stale = True
    for event in events:
        # Check staleness
        if event.occurred_at:
            age_days = (reference_time - event.occurred_at).total_seconds() / 86400
            if age_days <= half_life_days:
                stale = False
        else:
            # If no time, assume fresh or handled differently? Prompt says "evidence within half-life".
            # Let's assume it's fresh if no occurred_at.
            stale = False

        if event.origin_key:
            independent_sources.add(event.origin_key)
        else:
            # If no origin_key, each event could be considered unique or same? Let's use event_id as fallback
            independent_sources.add(event.event_id)

        r_idx = ['A', 'B', 'C', 'D', 'E', 'F'].index(event.source_reliability) if event.source_reliability in ['A', 'B', 'C', 'D', 'E', 'F'] else 5
        c_idx = event.info_credibility
        
        # B2 or better: reliability <= 'B' (index 1), credibility <= 2
        if r_idx <= 1 and c_idx <= 2:
            b2_or_better_count += 1
        # C3 or better: reliability <= 'C' (index 2), credibility <= 3
        if r_idx <= 2 and c_idx <= 3:
            c3_or_better_count += 1
            
    num_independent = len(independent_sources)
    all_d4_or_worse = (c3_or_better_count == 0) # D4 or worse is everything not C3 or better
    
    if num_independent >= 3 and b2_or_better_count >= 1 and not stale:
        return AnalyticConfidence.HIGH
    elif num_independent >= 2 and c3_or_better_count >= 1:
        return AnalyticConfidence.MODERATE
    elif num_independent == 1 or all_d4_or_worse or stale:
        return AnalyticConfidence.LOW
    
    return AnalyticConfidence.LOW

