import pytest
import os
from unittest.mock import patch
from shared.models import SeverityTier
from coptoc.classifier.client import ClassifierClient
from coptoc.classifier.models import ClassificationResult

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
