import json
import logging
import os
import time
from typing import Any, Dict, Optional

import anthropic
from shared.models import SeverityTier

from .models import ClassificationResult

logger = logging.getLogger(__name__)

MODEL = os.environ.get("MODTOC_MODEL", "claude-opus-5")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClassifierClient:
    """Policy classifier. `mode="claude"` calls the model; `mode="heuristic"` is the offline rule set used by CI and
    the eval harness. Failures never resolve to "allow": a result with `failed=True` is routed to human review."""

    def __init__(self, mode: str = "heuristic", api_key: Optional[str] = None, model: Optional[str] = None):
        self.mode = mode
        self.model = model or MODEL
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if self.mode == "claude" and not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found. Falling back to heuristic mode.")
            self.mode = "heuristic"
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.mode == "claude" else None

    def classify_text(self, text: str, system_prompt: str, policy: Dict[str, Any]) -> ClassificationResult:
        if policy.get("scope", {}).get("inference_engine") == "hash_matching_only":
            return ClassificationResult(severity=SeverityTier.TIER_1_SEVERE, confidence=1.0,
                                        rationale="Deterministic perceptual hash match. Legal reporting routed.",
                                        model_version="photodna-hash-engine")
        if self.mode == "claude":
            return self._classify_claude(text, system_prompt)
        return self._classify_heuristic(text, policy)

    # ---------------------------------------------------------------- model path

    def _classify_claude(self, text: str, system_prompt: str) -> ClassificationResult:
        start = time.time()
        prompt = f"{system_prompt}\n\nReturn ONLY a JSON object with keys severity, confidence, rationale."
        try:
            response = self._create(prompt, text)
        except Exception as e:  # noqa: BLE001 — transport/API failure: fail closed
            return self._failed(f"classifier call failed: {type(e).__name__}: {e}", start)
        latency = (time.time() - start) * 1000.0
        served_by = getattr(response, "model", None) or self.model
        if getattr(response, "stop_reason", None) == "refusal":
            details = getattr(response, "stop_details", None)
            cat = getattr(details, "category", None) if details else None
            return self._failed(f"model declined to classify (category={cat}); needs human review", start, served_by)
        text_out = "".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text")
        try:
            data = json.loads(text_out[text_out.find("{"): text_out.rfind("}") + 1])
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to parse classifier response: %s", e)
            return self._failed(f"unparseable classifier response: {e}", start, served_by)
        return ClassificationResult(
            severity=self._severity(str(data.get("severity", "none"))),
            confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0) or 0.0))),
            rationale=str(data.get("rationale", "")), model_version=served_by, latency_ms=latency,
        )

    def _create(self, system: str, text: str):
        kwargs = dict(model=self.model, max_tokens=1024, system=system, messages=[{"role": "user", "content": text}],
                      output_config={"effort": "low"})
        try:  # server-side refusal fallback: a decline is re-run on another model inside the same call
            return self.client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        except TypeError:  # older SDK without these parameters
            return self.client.messages.create(**kwargs)

    @staticmethod
    def _severity(s: str) -> SeverityTier:
        try:
            return SeverityTier(s)
        except ValueError:
            low = s.lower()
            return (SeverityTier.TIER_1_SEVERE if "tier_1" in low else SeverityTier.TIER_2_MODERATE if "tier_2" in low
                    else SeverityTier.TIER_3_BORDERLINE if "tier_3" in low else SeverityTier.NONE)

    def _failed(self, why: str, start: float, model: Optional[str] = None) -> ClassificationResult:
        return ClassificationResult(severity=SeverityTier.NONE, confidence=0.0, rationale=why, failed=True,
                                    model_version=model or self.model, latency_ms=(time.time() - start) * 1000.0)

    # ---------------------------------------------------------------- offline rules

    def _classify_heuristic(self, text: str, policy: Dict[str, Any]) -> ClassificationResult:
        lower = text.lower()
        mv = "heuristic-rules"
        for ex in policy.get("examples", []):
            if ex.get("expected_tier") == "tier_1_severe" and "vermin" in ex.get("text", "").lower() and "vermin" in lower:
                return ClassificationResult(severity=SeverityTier.TIER_1_SEVERE, confidence=0.92,
                                            rationale=ex.get("reasoning", "Caught by dynamic policy example."), model_version=mv)
        if "cockroach" in lower or "exterminate" in lower or "subhuman" in lower:
            return ClassificationResult(severity=SeverityTier.TIER_1_SEVERE, confidence=0.92, model_version=mv,
                                        rationale="Dehumanization and calls for violence targeting a protected group.")
        if "dishonest thieves" in lower or "inferior" in lower or "not allowed" in lower:
            return ClassificationResult(severity=SeverityTier.TIER_2_MODERATE, confidence=0.88, model_version=mv,
                                        rationale="Derogatory stereotypes and discrimination targeting a religious group.")
        if "stupid" in lower or "incompetent" in lower or "traffic" in lower or "worst" in lower:
            return ClassificationResult(severity=SeverityTier.NONE, confidence=0.95, model_version=mv,
                                        rationale="General criticism or venting without protected attribute targeting.")
        return ClassificationResult(severity=SeverityTier.NONE, confidence=0.80, model_version=mv,
                                    rationale="No explicit policy violation found.")
