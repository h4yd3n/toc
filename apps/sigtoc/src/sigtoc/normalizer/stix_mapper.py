import uuid
from typing import List
from shared.models import STIXThreatObject, ThreatReport


class STIXMapper:
    """Normalizes ThreatReports into STIX 2.1 compliant objects."""

    @staticmethod
    def to_stix_bundle(report: ThreatReport) -> List[STIXThreatObject]:
        objects = []
        # Threat Actor
        for actor in report.threat_actors:
            objects.append(
                STIXThreatObject(
                    id=f"threat-actor--{uuid.uuid4()}",
                    type="threat-actor",
                    name=actor,
                    description=f"Adversary discovered via {report.source}",
                    labels=["coordinated-campaign", "t&s-adversary"],
                    confidence=int(report.credibility_score * 100),
                )
            )

        # Attack Pattern (Evasion Tactic)
        for tactic in report.evasion_tactics:
            objects.append(
                STIXThreatObject(
                    id=f"attack-pattern--{uuid.uuid4()}",
                    type="attack-pattern",
                    name=tactic,
                    description=f"Bypass pattern: {report.summary}",
                    labels=["filter-evasion", "policy-bypass"],
                    confidence=int(report.credibility_score * 100),
                )
            )
        return objects
