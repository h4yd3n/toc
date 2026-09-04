import os
from modtoc.evals.harness import run_eval_harness, format_markdown_diff_comment

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../modtoc'))

def test_golden_set_evaluation_and_diff_report():
    policy_path = os.path.join(ROOT, 'policies/hate_speech.yaml')
    golden_path = os.path.join(ROOT, 'evals/golden_sets/hate_speech_golden.json')
    
    report = run_eval_harness(policy_path, golden_path)
    assert report['total_cases'] == 4
    assert report['accuracy'] == 100.0
    assert report['flips'] == 0

    comment = format_markdown_diff_comment(report)
    assert "Coptoc Policy-Diff CI Report" in comment
    assert "100.0%" in comment
