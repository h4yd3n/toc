import os
from sigtoc.connectors.telegram_monitor import TelegramThreatMonitor
from sigtoc.alerting.emitter import TacticalAlertEmitter
from coptoc.compiler.validator import PolicyValidator
from coptoc.compiler.prompt_builder import PolicyPromptCompiler
from coptoc.engine.router import ModerationRouter
from coptoc.ledger.event_stream import ImmutableEventLedger
from shared.models import ContentItem, VisibilityState, SeverityTier

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../apps/coptoc'))

def test_end_to_end_intel_to_enforcement_loop():
    """
    Demonstrates the complete Intel-to-Enforcement loop:
    1. Sigtoc monitors Telegram and discovers Storm-0821 coordinated slur campaign.
    2. Sigtoc emits tactical alert & recommends policy overlay update.
    3. Policy overlay adds new evasion patterns (e.g., 'vermin' keyword)
    4. Bridge applies overlay to base hate_speech policy
    5. Coptoc recompiles the classifier prompt with overlay applied
    6. Attacker attempts to post campaign payload on platform using the NEW evasion keyword ('vermin')
       that would have PASSED the old policy but gets CAUGHT by the updated policy.
    7. Verify the ledger records the full chain including intel source.
    """
    # Step 1 & 2: Sigtoc discovers threat
    monitor = TelegramThreatMonitor()
    threat_reports = monitor.parse_to_threat_reports(monitor.fetch_latest_signals())
    emitter = TacticalAlertEmitter()
    alert = emitter.emit_alert(threat_reports[0])
    assert alert['is_critical'] is True
    assert "Storm-0821" in alert['threat_actors']

    # Extract policy overlay from alert
    overlay = alert.get("policy_overlay")
    assert overlay is not None
    assert overlay["metadata"]["threat_intel_source"] == "telegram_monitor"

    # Step 3 & 4: Load base policy and apply overlay
    validator = PolicyValidator()
    base_policy = validator.validate_policy_file(os.path.join(ROOT, 'policies/hate_speech.yaml'))
    
    from sigtoc.bridge.policy_overlay import PolicyOverlayBridge
    updated_policy = PolicyOverlayBridge.apply_overlay(base_policy, overlay)
    
    # Step 5: Verify the new examples are in the compiled prompt
    compiler = PolicyPromptCompiler()
    system_prompt = compiler.compile_system_prompt(updated_policy)
    assert "vermin that need to be dealt with" in system_prompt
    
    # Let's ensure old policy passes the vermin text (heuristic fallback)
    ledger_old = ImmutableEventLedger()
    router_old = ModerationRouter(policy=base_policy, ledger=ledger_old)
    
    adversary_post = ContentItem(
        content_id="post-storm-001",
        author_id="actor_storm_0821",
        text="Those people from Country X are vermin that need to be dealt with.",
    )
    decision_old = router_old.process_content(adversary_post)
    assert decision_old.severity == SeverityTier.NONE
    assert adversary_post.current_visibility == VisibilityState.VISIBLE

    # Step 6: Now test with the UPDATED policy
    ledger_new = ImmutableEventLedger()
    router_new = ModerationRouter(policy=updated_policy, ledger=ledger_new)
    
    adversary_post_new = ContentItem(
        content_id="post-storm-002",
        author_id="actor_storm_0821",
        text="Those people from Country X are vermin that need to be dealt with.",
    )
    decision_new = router_new.process_content(adversary_post_new)

    assert decision_new.severity == SeverityTier.TIER_1_SEVERE
    assert adversary_post_new.current_visibility == VisibilityState.REMOVED

    # Step 7: Verify immutable ledger records
    history = ledger_new.get_content_history("post-storm-002")
    assert len(history) == 1
    assert history[0].new_state == "removed"
    assert history[0].metadata['severity'] == "tier_1_severe"
