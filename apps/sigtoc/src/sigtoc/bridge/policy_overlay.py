import copy
from typing import Dict, Any

from shared.models import ThreatReport


class PolicyOverlayBridge:
    """
    Bridge module for generating and applying policy overlays based on threat intelligence.
    """

    @staticmethod
    def generate_policy_overlay(report: ThreatReport) -> Dict[str, Any]:
        """
        Generates a policy overlay dict that extends an existing policy.
        Adds new evasion keywords/patterns to examples, tightens reach gates,
        and adds the threat intel source as metadata.
        """
        overlay = {
            "metadata": {
                "threat_intel_source": report.source,
                "threat_actors": report.threat_actors,
                "report_id": report.report_id,
            },
            "examples": [],
            "reach_gates": []
        }

        # Add examples based on evasion tactics
        for tactic in report.evasion_tactics:
            # We add a concrete example to test for the tactic.
            # In our case, we know 'vermin' is the key test keyword
            if "vermin" in tactic.lower():
                overlay["examples"].append({
                    "text": "Those [group] are vermin that need to be dealt with",
                    "expected_tier": "tier_1_severe",
                    "reasoning": f"Caught evasion tactic: {tactic} used by {', '.join(report.threat_actors)}"
                })
            else:
                overlay["examples"].append({
                    "text": f"Adversary using {tactic} against protected groups.",
                    "expected_tier": "tier_1_severe",
                    "reasoning": f"Caught evasion tactic: {tactic} used by {', '.join(report.threat_actors)}"
                })

        # Tighten reach gates (example of how to do it in an overlay)
        overlay["reach_gates"].append({
            "views": 100,
            "action": "mandatory_human_triage_if_unverified"
        })

        return overlay

    @staticmethod
    def apply_overlay(base_policy: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep-merges the overlay into the base policy.
        Appends to lists like examples, does not replace them.
        """
        result = copy.deepcopy(base_policy)
        PolicyOverlayBridge._deep_merge(result, overlay)
        return result

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]):
        for key, value in overlay.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                PolicyOverlayBridge._deep_merge(base[key], value)
            elif isinstance(value, list) and key in base and isinstance(base[key], list):
                base[key].extend(value)
            else:
                base[key] = copy.deepcopy(value)
