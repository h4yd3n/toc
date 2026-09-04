import uuid
from typing import Any, Dict, Optional
from shared.models import ContentItem, ModerationDecision, VisibilityState
from ..classifier.client import ClassifierClient
from ..compiler.prompt_builder import PolicyPromptCompiler
from ..compiler.routing_generator import RoutingTableGenerator
from shared.ledger import ImmutableEventLedger
from .state_machine import VisibilityStateMachine
from .reach_gates import ReachGateManager


class ModerationRouter:
    """
    Core Moderation Orchestrator:
    1. Runs classification against policy prompt.
    2. Resolves decision via Severity x Confidence routing matrix.
    3. Enforces valid state machine transition.
    4. Appends audit record to immutable event ledger.
    """

    def __init__(
        self,
        policy: Dict[str, Any],
        classifier: Optional[ClassifierClient] = None,
        ledger: Optional[ImmutableEventLedger] = None,
        reach_gate: Optional[ReachGateManager] = None,
    ):
        self.policy = policy
        self.classifier = classifier or ClassifierClient()
        self.ledger = ledger or ImmutableEventLedger()
        self.reach_gate = reach_gate or ReachGateManager()
        self.system_prompt = PolicyPromptCompiler.compile_system_prompt(policy)

    def process_content(self, item: ContentItem) -> ModerationDecision:
        # Step 1: Classify content
        result = self.classifier.classify_text(item.text, self.system_prompt, self.policy)

        # Step 2: Route via matrix
        action, target_vis, route_name = RoutingTableGenerator.resolve_decision(
            self.policy, result.severity, result.confidence
        )

        # REACH GATE OVERRIDE CHECK
        tripped_gate = self.reach_gate.check_reach_gate_tripped(0, item.view_count)
        if tripped_gate is not None:
            self.ledger.append_event(
                content_id=item.content_id,
                event_type="reach_gate_tripped",
                actor_type="reach_gate",
                actor_id="reach_gate_manager",
                reason=f"Crossed reach gate {tripped_gate}",
                metadata={"gate": tripped_gate, "views": item.view_count}
            )
            if not item.metadata.get("human_verified", False):
                if tripped_gate >= 300_000 and result.severity.value != "none":
                    target_vis = VisibilityState.HELD
                elif tripped_gate >= 30_000 and item.current_visibility == VisibilityState.VISIBLE and result.severity.value != "none":
                    target_vis = VisibilityState.LIMITED

        # Step 3: State transition
        new_vis, valid = VisibilityStateMachine.transition(item.current_visibility, target_vis)
        old_vis = item.current_visibility
        item.current_visibility = new_vis

        decision = ModerationDecision(
            decision_id=f"DEC-{uuid.uuid4().hex[:12]}",
            content_id=item.content_id,
            policy_id=self.policy.get("policy_id", "UNKNOWN"),
            policy_version=self.policy.get("version", "1.0.0"),
            severity=result.severity,
            confidence=result.confidence,
            action=action,
            new_visibility=new_vis,
            rationale=result.rationale,
            actor=result.model_version,
        )

        # Step 4: Immutable audit ledger entry
        self.ledger.append_event(
            content_id=item.content_id,
            event_type="moderation_decision",
            actor_type="ai_model",
            actor_id=result.model_version,
            policy_version=self.policy.get("version"),
            old_state=old_vis.value,
            new_state=new_vis.value,
            reason=result.rationale,
            metadata={
                "decision_id": decision.decision_id,
                "action": action.value,
                "severity": result.severity.value,
                "confidence": result.confidence,
                "route_instruction": route_name,
            },
        )

        return decision
