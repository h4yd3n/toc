from typing import Any, Dict, List, Optional
from shared.constants import DEFAULT_REACH_GATES
from shared.models import ContentItem, VisibilityState


class ReachGateManager:
    """
    Escalating mandatory review gates:
    300 -> 3K -> 30K -> 300K -> 3M views.
    Enforces that high-reach content receives escalating verification,
    structurally bounding worst-case harm at viral scale.
    """

    def __init__(self, gates: Optional[List[int]] = None):
        self.gates = sorted(gates or DEFAULT_REACH_GATES)

    def check_reach_gate_tripped(
        self, old_views: int, new_views: int
    ) -> Optional[int]:
        for g in reversed(self.gates):
            if old_views < g <= new_views:
                return g
        return None

    def evaluate_gate_requirement(self, gate: int) -> str:
        if gate <= 300:
            return "low_cost_classifier_check"
        elif gate <= 3_000:
            return "model_ensemble_check"
        elif gate <= 30_000:
            return "statistical_qa_sample"
        elif gate <= 300_000:
            return "mandatory_human_review_if_unverified"
        else:
            return "hard_bound_mandatory_human_signoff"
