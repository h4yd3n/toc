"""FIXTURE — a hard-coded synthetic threat signal.

Stands in for a closed-source adversary feed so the intel→enforcement loop (ThreatReport → PolicyOverlayBridge →
moderation policy) can be exercised without one. It does not connect to anything, and it must never be presented
as a collector. Real collectors live in `sigtoc.collectors` and are tagged `synthetic=False` on the wall."""
import uuid
from typing import Any, Dict, List

from shared.models import ThreatReport


class FixtureThreatFeed:
    source_name = "fixture:threat_feed"

    def fetch_latest_signals(self) -> List[Dict[str, Any]]:
        return [{
            "channel": "fixture",
            "message_id": "9921",
            "text": "Campaign Alpha: Use bypass tokens '[Country X] vermin' starting at 20:00 UTC to flood feed.",
            "threat_actor": "Storm-0821",
            "evasion_pattern": "vermin / cockroach replacement tokens",
            "target": "Platform Feed & SoriStory Community",
        }]

    def parse_to_threat_reports(self, raw_signals: List[Dict[str, Any]]) -> List[ThreatReport]:
        return [ThreatReport(
            report_id=f"RPT-FX-{uuid.uuid4().hex[:8]}", source=self.source_name,
            title=f"Coordinated Evasion Campaign from {s.get('threat_actor')}", summary=s.get("text", ""),
            severity_score=8.5, credibility_score=0.90, relevance_score=0.95,
            threat_actors=[s.get("threat_actor", "Unknown")], evasion_tactics=[s.get("evasion_pattern", "token_bypass")],
            recommended_policy_action="update_hate_speech_slur_overlay_and_tighten_reach_gate_1",
        ) for s in raw_signals]
