from typing import List, Optional
from shared.models import DimensionScore, AnalyticConfidence

def check_refuse_to_score(
    dimension_scores: List[DimensionScore],
) -> Optional[str]:
    if not dimension_scores:
        return None
        
    total_weight = sum(ds.weight for ds in dimension_scores)
    if total_weight == 0:
        return None
        
    insufficient_dims = []
    insufficient_weight = 0.0
    
    for ds in dimension_scores:
        if ds.analytic_confidence == AnalyticConfidence.INSUFFICIENT:
            insufficient_dims.append(ds.dimension)
            insufficient_weight += ds.weight
            
    pct = (insufficient_weight / total_weight) * 100
    
    if pct > 20.0:
        # Format names, e.g. "espionage" -> "Espionage", "legal_risk" -> "Legal Risk"
        formatted_names = [d.replace('_', ' ').title() for d in insufficient_dims]
        if len(formatted_names) == 1:
            dims_str = formatted_names[0]
        elif len(formatted_names) == 2:
            dims_str = f"{formatted_names[0]} and {formatted_names[1]}"
        else:
            dims_str = ", ".join(formatted_names[:-1]) + f", and {formatted_names[-1]}"
            
        return f"Assessment incomplete — no qualifying collection on {dims_str}, which carry {int(round(pct))}% of mission weight for this trip profile."
        
    return None
