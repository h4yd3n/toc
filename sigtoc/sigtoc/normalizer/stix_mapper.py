import uuid
from typing import List
from shared.models import STIXThreatObject, ThreatReport


class STIXMapper:
    """Normalizes ThreatReports into STIX 2.1 compliant objects."""

    @staticmethod
    def to_stix_bundle(report: ThreatReport) -> List[STIXThreatObject]:
        objects = []
        campaign_labels = ["coordinated-campaign"]
        if report.campaign_type:
            campaign_labels.append(report.campaign_type.replace("_", "-"))
        if report.state_nexus:
            campaign_labels.append(f"state-nexus:{report.state_nexus.lower()}")

        # STIX Campaign (if specified)
        if report.campaign_type:
            objects.append(
                STIXThreatObject(
                    id=f"campaign--{uuid.uuid4()}",
                    type="campaign",
                    name=report.title,
                    description=report.summary,
                    labels=campaign_labels + ["foreign-influence" if report.state_nexus else "influence-operation"],
                    confidence=int(report.credibility_score * 100),
                )
            )

        # Threat Actor
        actor_labels = ["coordinated-campaign", "t&s-adversary"]
        if report.state_nexus:
            actor_labels.append(f"state-nexus:{report.state_nexus.lower()}")
        if report.campaign_type in ("influence_operation", "coordinated_inauthentic_behavior"):
            actor_labels.append("influence-operator")
        elif report.campaign_type == "conventional_weapons":
            actor_labels.extend(["kinetic-adversary", "weapons-developer"])
        elif report.campaign_type == "cyber_espionage":
            actor_labels.extend(["cyber-espionage", "state-nexus-espionage"])

        if any(a.startswith("GTG-") for a in report.threat_actors):
            actor_labels.append("generative-threat-group")

        for actor in report.threat_actors:
            objects.append(
                STIXThreatObject(
                    id=f"threat-actor--{uuid.uuid4()}",
                    type="threat-actor",
                    name=actor,
                    description=f"Adversary discovered via {report.source}",
                    labels=actor_labels,
                    confidence=int(report.credibility_score * 100),
                )
            )

        # Attack Pattern (Evasion / Influence / Kinetic Tactic)
        if report.campaign_type in ("influence_operation", "coordinated_inauthentic_behavior"):
            pattern_labels = ["influence-technique", "coordinated-behavior"]
        elif report.campaign_type == "conventional_weapons":
            pattern_labels = ["autonomous-weapons", "kinetic-capability"]
        elif report.campaign_type == "cyber_espionage":
            pattern_labels = ["supply-chain-interception", "cyber-exploit"]
        else:
            pattern_labels = ["filter-evasion", "policy-bypass"]

        for tactic in report.evasion_tactics:
            objects.append(
                STIXThreatObject(
                    id=f"attack-pattern--{uuid.uuid4()}",
                    type="attack-pattern",
                    name=tactic,
                    description=f"Technique pattern: {report.summary}",
                    labels=pattern_labels,
                    confidence=int(report.credibility_score * 100),
                )
            )
        return objects
