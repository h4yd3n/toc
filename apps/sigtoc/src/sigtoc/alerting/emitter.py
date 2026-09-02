from typing import Dict, List, Optional
from shared.models import ThreatReport
from ..scoring.scorer import ThreatScorer
from ..bridge.policy_overlay import PolicyOverlayBridge


class TacticalAlertEmitter:
    """
    Emits real-time alerts to the TOC Common Operating Picture and
    triggers automated policy-update bridges into Coptoc.
    """

    def __init__(self):
        self.alert_history: List[Dict] = []

    def generate_policy_overlay(self, report: ThreatReport) -> Dict:
        return PolicyOverlayBridge.generate_policy_overlay(report)

    def emit_alert(self, report: ThreatReport) -> Dict:
        priority_score = ThreatScorer.calculate_priority_score(report)
        is_critical = ThreatScorer.is_critical_escalation(report)

        alert = {
            "alert_id": f"ALT-{report.report_id}",
            "title": f"🚨 [TOC ALERT]: {report.title}",
            "priority_score": priority_score,
            "is_critical": is_critical,
            "source": report.source,
            "threat_actors": report.threat_actors,
            "recommended_action": report.recommended_policy_action,
            "status": "active_investigation",
        }
        
        if is_critical:
            alert["policy_overlay"] = self.generate_policy_overlay(report)
            
        self.alert_history.append(alert)
        return alert

    def get_active_alerts(self) -> List[Dict]:
        return list(self.alert_history)
