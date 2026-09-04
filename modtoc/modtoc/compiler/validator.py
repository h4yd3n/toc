import json
import os
from typing import Any, Dict
import jsonschema
import yaml


class PolicyValidator:
    def __init__(self, schema_path: str = None):
        if schema_path is None:
            # Check standard package schema locations
            candidates = [
                os.path.join(os.path.dirname(__file__), "../../../schemas/policy.schema.json"),
                os.path.join(os.path.dirname(__file__), "../../schemas/policy.schema.json"),
                os.path.join(os.path.dirname(__file__), "policy.schema.json"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    schema_path = c
                    break
        
        if not schema_path or not os.path.exists(schema_path):
            raise FileNotFoundError(f"Cannot locate policy.schema.json at {schema_path}")

        with open(schema_path, "r") as f:
            self.schema = json.load(f)

    def validate_policy_dict(self, policy: Dict[str, Any]) -> bool:
        jsonschema.validate(instance=policy, schema=self.schema)
        # Custom architectural invariant: CSAM must never use LLM inference
        if "csam" in policy.get("policy_id", "").lower():
            engine = policy.get("scope", {}).get("inference_engine", "")
            if engine != "hash_matching_only":
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: Policy {policy.get('policy_id')} involves CSAM/CSAE "
                    f"and must have inference_engine set to 'hash_matching_only', got '{engine}'."
                )
        return True

    def validate_policy_file(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
        self.validate_policy_dict(data)
        return data
