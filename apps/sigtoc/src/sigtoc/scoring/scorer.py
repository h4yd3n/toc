from shared.models import ThreatReport


class ThreatScorer:
    """
    Calculates threat priority score:
    Composite Score = Severity (0-10) * Credibility (0-1) * Relevance (0-1).
    """

    @staticmethod
    def calculate_priority_score(report: ThreatReport) -> float:
        composite = report.severity_score * report.credibility_score * report.relevance_score
        return round(composite, 2)

    @staticmethod
    def is_critical_escalation(report: ThreatReport) -> bool:
        score = ThreatScorer.calculate_priority_score(report)
        return score >= 6.50
