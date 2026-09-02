import os
import pytest
from coptoc.compiler.validator import PolicyValidator
from coptoc.compiler.prompt_builder import PolicyPromptCompiler
from coptoc.compiler.routing_generator import RoutingTableGenerator
from shared.models import SeverityTier, EnforcementAction, VisibilityState

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../apps/coptoc'))

def test_validate_hate_speech_policy():
    validator = PolicyValidator()
    policy_path = os.path.join(ROOT, 'policies/hate_speech.yaml')
    policy = validator.validate_policy_file(policy_path)
    assert policy['policy_id'] == 'POL-HATE-001'
    assert policy['version'] == '1.2.0'

def test_csam_zero_llm_invariant_enforcement():
    validator = PolicyValidator()
    csam_path = os.path.join(ROOT, 'policies/csam_csae.yaml')
    policy = validator.validate_policy_file(csam_path)
    assert policy['scope']['inference_engine'] == 'hash_matching_only'

    # Verify that trying to use LLM for CSAM raises an explicit safety exception
    invalid_csam = dict(policy)
    invalid_csam['scope'] = {'inference_engine': 'llm', 'supported_modalities': ['text']}
    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        validator.validate_policy_dict(invalid_csam)

def test_prompt_compiler_generates_few_shot_examples():
    validator = PolicyValidator()
    policy = validator.validate_policy_file(os.path.join(ROOT, 'policies/hate_speech.yaml'))
    prompt = PolicyPromptCompiler.compile_system_prompt(policy)
    assert "You are the Trust & Safety Classifier Engine" in prompt
    assert "CALIBRATION EXAMPLES (FEW-SHOT)" in prompt
    assert "tier_1_severe" in prompt

def test_routing_table_matrix_resolution():
    validator = PolicyValidator()
    policy = validator.validate_policy_file(os.path.join(ROOT, 'policies/hate_speech.yaml'))
    
    # Tier 1 with High Confidence -> REMOVE_AND_STRIKE / REMOVED
    action, vis, route = RoutingTableGenerator.resolve_decision(policy, SeverityTier.TIER_1_SEVERE, 0.95)
    assert action == EnforcementAction.REMOVE_AND_STRIKE
    assert vis == VisibilityState.REMOVED

    # Tier 2 with High Confidence -> RESTRICT_VISIBILITY / LIMITED
    action, vis, route = RoutingTableGenerator.resolve_decision(policy, SeverityTier.TIER_2_MODERATE, 0.90)
    assert action == EnforcementAction.RESTRICT_VISIBILITY
    assert vis == VisibilityState.LIMITED

    # None -> ALLOW / VISIBLE
    action, vis, route = RoutingTableGenerator.resolve_decision(policy, SeverityTier.NONE, 0.99)
    assert action == EnforcementAction.ALLOW
    assert vis == VisibilityState.VISIBLE
