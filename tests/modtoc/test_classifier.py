import pytest
import os
from unittest.mock import patch
from shared.models import SeverityTier
from modtoc.classifier.client import ClassifierClient
from modtoc.classifier.models import ClassificationResult

def test_heuristic_mode_hate_speech():
    client = ClassifierClient(mode='heuristic')
    result = client.classify_text("Those people are cockroaches and need to be exterminated.", "sys_prompt", {})
    assert result.severity == SeverityTier.TIER_1_SEVERE

def test_heuristic_mode_benign():
    client = ClassifierClient(mode='heuristic')
    result = client.classify_text("The traffic was worst today.", "sys_prompt", {})
    assert result.severity == SeverityTier.NONE

def test_claude_mode_falls_back_without_api_key():
    with patch.dict(os.environ, clear=True):
        client = ClassifierClient(mode='claude')
        assert client.mode == 'heuristic'
        result = client.classify_text("cockroach", "sys_prompt", {})
        assert result.severity == SeverityTier.TIER_1_SEVERE

def test_classification_result_has_latency():
    result = ClassificationResult(
        severity=SeverityTier.NONE,
        confidence=1.0,
        rationale="test",
        latency_ms=150.5
    )
    assert result.latency_ms == 150.5


# ---- fail-closed behaviour and honest ledger attribution (no network: fake responses) ----
import os as _os
from types import SimpleNamespace as _NS
from modtoc.compiler.validator import PolicyValidator
from modtoc.engine.router import ModerationRouter
from shared.models import ContentItem, EnforcementAction, VisibilityState

_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "../../modtoc"))

def _fake_client(response):
    class _Msgs:
        def create(self, **kw): return response
    return _NS(beta=_NS(messages=_Msgs()), messages=_Msgs())

def _claude_client(response):
    c = ClassifierClient(mode="heuristic")
    c.mode, c.client, c.model = "claude", _fake_client(response), "claude-opus-5"
    return c

def test_model_path_reads_text_blocks_after_thinking_and_records_serving_model():
    resp = _NS(model="claude-opus-4-8", stop_reason="end_turn", content=[
        _NS(type="thinking", thinking=""), _NS(type="text", text='Here: {"severity": "tier_1_severe", "confidence": 0.93, "rationale": "dehumanizing"}')])
    r = _claude_client(resp).classify_text("...", "sys", {})
    assert r.severity == SeverityTier.TIER_1_SEVERE and r.confidence == 0.93 and not r.failed
    assert r.model_version == "claude-opus-4-8"  # the model that answered (a fallback here), not the one we asked for

def test_refusal_and_garbage_fail_closed_not_open():
    refused = _NS(model="claude-opus-5", stop_reason="refusal", stop_details=_NS(category="hate"), content=[])
    garbage = _NS(model="claude-opus-5", stop_reason="end_turn", content=[_NS(type="text", text="I cannot help with that.")])
    for resp in (refused, garbage):
        r = _claude_client(resp).classify_text("...", "sys", {})
        assert r.failed is True and r.severity == SeverityTier.NONE
    # Through the router: a failed classification must NOT resolve to allow
    policy = PolicyValidator().validate_policy_file(_os.path.join(_ROOT, "policies/hate_speech.yaml"))
    router = ModerationRouter(policy=policy, classifier=_claude_client(garbage))
    d = router.process_content(ContentItem(content_id="c-fail", author_id="a", text="whatever"))
    assert d.action == EnforcementAction.RESTRICT_VISIBILITY and d.new_visibility == VisibilityState.LIMITED
    assert router.ledger.get_content_history("c-fail")[-1].metadata["classifier_failed"] is True

def test_heuristic_decisions_are_not_attributed_to_a_model():
    r = ClassifierClient(mode="heuristic").classify_text("you are all cockroaches", "sys", {})
    assert r.model_version == "heuristic-rules"
