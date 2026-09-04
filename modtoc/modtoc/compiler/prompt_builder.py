from typing import Any, Dict


class PolicyPromptCompiler:
    """
    Compiles a structured Policy YAML definition into an optimized system prompt
    with few-shot calibration examples for Claude / LLM classifiers.
    """

    @staticmethod
    def compile_system_prompt(policy: Dict[str, Any]) -> str:
        if policy.get("scope", {}).get("inference_engine") == "hash_matching_only":
            return "[ZERO-LLM POLICY]: This policy is executed exclusively via deterministic hash matching."

        name = policy.get("name", "Content Policy")
        policy_id = policy.get("policy_id", "UNKNOWN")
        version = policy.get("version", "1.0.0")
        definitions = policy.get("definitions", {})
        core_rule = definitions.get("core_rule", "").strip()
        protected = definitions.get("protected_characteristics", [])
        tiers = policy.get("severity_tiers", {})
        examples = policy.get("examples", [])

        lines = [
            f"You are the Trust & Safety Classifier Engine for policy: {name} (ID: {policy_id}, v{version}).",
            "",
            "### CORE POLICY DEFINITION:",
            core_rule,
            "",
        ]

        if protected:
            lines.append("### PROTECTED CHARACTERISTICS:")
            for p in protected:
                lines.append(f"- {p}")
            lines.append("")

        lines.append("### SEVERITY TIERS:")
        for tier_name, tier_data in tiers.items():
            lines.append(f"- **{tier_name}**: {tier_data.get('description', '')}")
        lines.append("- **none**: Content does not violate this policy.")
        lines.append("")

        if examples:
            lines.append("### CALIBRATION EXAMPLES (FEW-SHOT):")
            for ex in examples:
                lines.append(f"Text: \"{ex.get('text', '')}\"")
                lines.append(f"Classification: {ex.get('expected_tier')}")
                lines.append(f"Reasoning: {ex.get('reasoning', '')}")
                lines.append("---")
            lines.append("")

        lines.append("### OUTPUT INSTRUCTIONS:")
        lines.append("Return a JSON object containing:")
        lines.append("- \"severity\": one of [\"none\", \"tier_3_borderline\", \"tier_2_moderate\", \"tier_1_severe\"]")
        lines.append("- \"confidence\": float between 0.00 and 1.00")
        lines.append("- \"rationale\": concise factual explanation referencing the policy criteria")

        return "\n".join(lines).strip()
