import os
from coptoc.compiler.validator import PolicyValidator
from coptoc.engine.router import ModerationRouter
from coptoc.engine.reach_gates import ReachGateManager
from coptoc.engine.state_machine import VisibilityStateMachine
from coptoc.intake.report_aggregator import ReportAggregator, UserReport
from coptoc.ledger.event_stream import ImmutableEventLedger
from shared.models import ContentItem, VisibilityState, SeverityTier, EnforcementAction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../apps/coptoc'))

def test_reach_gates_escalation():
    rg = ReachGateManager()
    assert rg.check_reach_gate_tripped(100, 250) is None
    assert rg.check_reach_gate_tripped(250, 350) == 300
    assert rg.check_reach_gate_tripped(25_000, 35_000) == 30_000
    assert rg.check_reach_gate_tripped(2_500_000, 3_100_000) == 3_000_000
    assert rg.evaluate_gate_requirement(3_000_000) == "hard_bound_mandatory_human_signoff"

def test_anti_brigading_report_aggregator():
    agg = ReportAggregator(reporter_credibility_db={"trusted_flagger": 0.95, "spammer": 0.10})
    
    # 5 reports from the same spammer only register once with low weight
    for i in range(5):
        item = agg.ingest_report(UserReport(
            report_id=f"rep-{i}", content_id="post-123", reporter_id="spammer", reported_category="hate_speech"
        ))
    assert item.total_raw_reports == 1
    assert item.requires_human_triage is False

    # Trusted flagger report has high weight
    item2 = agg.ingest_report(UserReport(
        report_id="rep-trusted", content_id="post-123", reporter_id="trusted_flagger", reported_category="hate_speech"
    ))
    assert item2.total_raw_reports == 2
    assert item2.weighted_score > 0.50

def test_moderation_router_and_immutable_ledger():
    validator = PolicyValidator()
    policy = validator.validate_policy_file(os.path.join(ROOT, 'policies/hate_speech.yaml'))
    ledger = ImmutableEventLedger()
    router = ModerationRouter(policy=policy, ledger=ledger)

    item = ContentItem(
        content_id="post-999",
        author_id="user-1",
        text="People from [Country X] are literal cockroaches that should be exterminated.",
    )
    decision = router.process_content(item)
    assert decision.severity == SeverityTier.TIER_1_SEVERE
    assert decision.action == EnforcementAction.REMOVE_AND_STRIKE
    assert item.current_visibility == VisibilityState.REMOVED

    history = ledger.get_content_history("post-999")
    assert len(history) == 1
    assert history[0].actor_type == "ai_model"
    assert history[0].new_state == "removed"

def test_reach_gates_wired_into_router():
    from coptoc.classifier.client import ClassifierClient
    
    class MockClassifier(ClassifierClient):
        def classify_text(self, text, system_prompt, policy):
            from shared.models import SeverityTier
            class MockResult:
                severity = SeverityTier.TIER_3_BORDERLINE
                confidence = 0.9
                rationale = "borderline"
                model_version = "mock-1.0"
            return MockResult()

    policy = {"policy_id": "test", "version": "1.0", "thresholds": {"tier_3_borderline": 0.5}, "routes": []}
    ledger = ImmutableEventLedger()
    router = ModerationRouter(policy=policy, ledger=ledger, classifier=MockClassifier())
    item = ContentItem(content_id="rg-123", author_id="a1", text="borderline text", view_count=350000)
    decision = router.process_content(item)
    
    assert decision.new_visibility in [VisibilityState.HELD, VisibilityState.LIMITED]
    assert decision.new_visibility != VisibilityState.VISIBLE
    
    history = ledger.get_content_history("rg-123")
    assert any(e.event_type == "reach_gate_tripped" for e in history)

def test_removed_to_limited_appeal():
    new_state, valid = VisibilityStateMachine.transition(VisibilityState.REMOVED, VisibilityState.LIMITED)
    assert valid is True
    assert new_state == VisibilityState.LIMITED

def test_ledger_hash_chain_integrity():
    ledger = ImmutableEventLedger()
    ledger.append_event("c1", "t1", "a", "a1")
    ledger.append_event("c1", "t2", "a", "a1")
    ledger.append_event("c1", "t3", "a", "a1")
    
    assert ledger.verify_chain_integrity("c1") is True
    history = ledger.get_content_history("c1")
    import hashlib
    assert history[1].prev_hash == hashlib.sha256(history[0].model_dump_json().encode('utf-8')).hexdigest()
