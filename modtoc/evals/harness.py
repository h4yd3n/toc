import argparse
import os
import json
from typing import Dict, List
from shared.models import ContentItem
from modtoc.compiler.validator import PolicyValidator
from modtoc.classifier.client import ClassifierClient
from modtoc.engine.router import ModerationRouter


def run_eval_harness(policy_path: str, golden_set_path: str) -> Dict:
    validator = PolicyValidator()
    policy = validator.validate_policy_file(policy_path)
    router = ModerationRouter(policy)

    with open(golden_set_path, "r") as f:
        golden_set = json.load(f)

    results = []
    matches = 0
    flips = 0

    for item in golden_set:
        content = ContentItem(content_id=item["id"], author_id="eval_bot", text=item["text"])
        decision = router.process_content(content)
        is_match = decision.severity.value == item["expected_tier"]
        if is_match:
            matches += 1
        else:
            flips += 1

        results.append({
            "id": item["id"],
            "expected": item["expected_tier"],
            "actual": decision.severity.value,
            "action": decision.action.value,
            "match": is_match,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
        })

    accuracy = (matches / len(golden_set)) * 100 if golden_set else 0.0

    return {
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("version"),
        "total_cases": len(golden_set),
        "matches": matches,
        "flips": flips,
        "accuracy": accuracy,
        "results": results,
    }


def format_markdown_diff_comment(report: Dict) -> str:
    comment = "## 🛡️ Coptoc Policy-Diff CI Report\n\n"
    comment += f"**Policy:** `{report['policy_id']}` (v{report['policy_version']})\n"
    comment += f"**Golden Set Accuracy:** `{report['accuracy']:.1f}%` ({report['matches']}/{report['total_cases']} matched)\n"
    comment += f"**Decision Deltas / Flips:** `{report['flips']}`\n\n"
    comment += "| Test ID | Expected Tier | Actual Tier | Action Taken | Match? |\n"
    comment += "| :--- | :--- | :--- | :--- | :---: |\n"
    for r in report["results"]:
        status = "✅ PASS" if r["match"] else "⚠️ FLIP"
        comment += f"| `{r['id']}` | `{r['expected']}` | `{r['actual']}` | `{r['action']}` | {status} |\n"
    return comment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coptoc Policy-Diff CI Evaluation Harness")
    parser.add_argument("--policy", required=True, help="Path to policy YAML file")
    parser.add_argument("--golden", required=True, help="Path to golden eval JSON file")
    parser.add_argument("--output-comment", help="Optional file to write GitHub PR comment markdown")
    parser.add_argument("--mode", choices=["heuristic", "claude"], default=os.environ.get("MODTOC_CLASSIFIER", "heuristic"),
                        help="heuristic (offline, CI) or claude (needs ANTHROPIC_API_KEY; model from MODTOC_MODEL, default claude-opus-5)")
    args = parser.parse_args()

    report = run_eval_harness(args.policy, args.golden)
    md = format_markdown_diff_comment(report)
    print(md)

    if args.output_comment:
        with open(args.output_comment, "w") as f:
            f.write(md)
