from typing import Any, Dict, Tuple
from shared.models import EnforcementAction, SeverityTier, VisibilityState


class RoutingTableGenerator:
    """
    Translates policy YAML routing matrix and severity rules into deterministic
    runtime decision functions: (Severity x Confidence) -> (Action, NewVisibility).
    """

    @staticmethod
    def resolve_decision(
        policy: Dict[str, Any], severity: SeverityTier, confidence: float
    ) -> Tuple[EnforcementAction, VisibilityState, str]:
        if severity == SeverityTier.NONE or confidence < 0.20:
            return EnforcementAction.ALLOW, VisibilityState.VISIBLE, "allow_no_violation"

        # High confidence >= 0.85, Medium = 0.50-0.84, Low < 0.50
        conf_tier = (
            "high_confidence" if confidence >= 0.85
            else "medium_confidence" if confidence >= 0.50
            else "low_confidence"
        )

        matrix = policy.get("routing_matrix", {})
        tier_routes = matrix.get(severity.value, {})
        route_instruction = tier_routes.get(conf_tier, "pass_visible")

        # Map instruction to Action and Visibility State
        if "remove_and_strike" in route_instruction or "immediate_takedown" in route_instruction:
            return EnforcementAction.REMOVE_AND_STRIKE, VisibilityState.REMOVED, route_instruction
        elif "restrict_visibility" in route_instruction or "limited" in route_instruction:
            return EnforcementAction.RESTRICT_VISIBILITY, VisibilityState.LIMITED, route_instruction
        elif "downrank" in route_instruction:
            return EnforcementAction.DOWNRANK, VisibilityState.LIMITED, route_instruction
        elif "quarantine_held" in route_instruction:
            return EnforcementAction.RESTRICT_VISIBILITY, VisibilityState.HELD, route_instruction
        elif "human_review_queue" in route_instruction:
            # Interim visibility remains visible unless high-reach gate trips
            return EnforcementAction.RESTRICT_VISIBILITY, VisibilityState.LIMITED, route_instruction
        else:
            return EnforcementAction.ALLOW, VisibilityState.VISIBLE, route_instruction
