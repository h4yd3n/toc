from typing import List, Optional, Tuple
from shared.models import DimensionScore, RiskBand
from shared.constants import MITIGATION_CREDITS, SCORE_BANDS

def compute_composite(
    dimension_scores: List[DimensionScore],
    mitigations: Optional[List[str]] = None,
) -> Tuple[float, float, str, str]:
    if not dimension_scores:
        band, rec = SCORE_BANDS[0][0], SCORE_BANDS[0][3]
        return 0.0, 0.0, band, rec

    total_weighted_score = sum(ds.weight * ds.value for ds in dimension_scores)
    total_weight = sum(ds.weight for ds in dimension_scores)
    
    if total_weight == 0:
        inherent = 0.0
    else:
        inherent = total_weighted_score / total_weight

    mitigations = mitigations or []
    
    # Calculate credit product
    multiplier = 1.0
    for m in mitigations:
        if m in MITIGATION_CREDITS:
            credit_j = abs(MITIGATION_CREDITS[m])
            multiplier *= (1.0 - credit_j)
            
    residual = inherent * multiplier
    floor_val = 0.4 * inherent
    
    if residual < floor_val:
        residual = floor_val

    # Map to band
    band_name = SCORE_BANDS[-1][0]
    recommendation = SCORE_BANDS[-1][3]
    
    for b_name, min_val, max_val, rec in SCORE_BANDS:
        if b_name == SCORE_BANDS[-1][0]:
            if min_val <= residual <= max_val:
                band_name = b_name
                recommendation = rec
                break
        else:
            if min_val <= residual < max_val:
                band_name = b_name
                recommendation = rec
                break

    return inherent, residual, band_name, recommendation
