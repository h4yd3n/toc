from sigtoc.fixtures import FixtureThreatFeed
from sigtoc.normalizer.stix_mapper import STIXMapper
from sigtoc.fusion.graph import ThreatEntityGraph
from sigtoc.scoring.scorer import ThreatScorer
from sigtoc.alerting.emitter import TacticalAlertEmitter

def test_telegram_connector_and_scoring():
    monitor = FixtureThreatFeed()
    raw = monitor.fetch_latest_signals()
    assert len(raw) == 1
    
    reports = monitor.parse_to_threat_reports(raw)
    assert len(reports) == 1
    report = reports[0]
    
    score = ThreatScorer.calculate_priority_score(report)
    assert score > 7.0
    assert ThreatScorer.is_critical_escalation(report) is True

def test_stix_normalization_and_entity_graph():
    monitor = FixtureThreatFeed()
    reports = monitor.parse_to_threat_reports(monitor.fetch_latest_signals())
    report = reports[0]

    stix_objects = STIXMapper.to_stix_bundle(report)
    assert len(stix_objects) == 2  # Threat Actor and Attack Pattern

    graph = ThreatEntityGraph()
    for obj in stix_objects:
        graph.add_threat_entity(obj)

    graph.link_entities("Storm-0821", "vermin / cockroach replacement tokens", relationship="employs-tactic")
    neighbors = graph.get_related_entities("Storm-0821")
    assert "vermin / cockroach replacement tokens" in neighbors

def test_tactical_alert_emitter():
    emitter = TacticalAlertEmitter()
    monitor = FixtureThreatFeed()
    report = monitor.parse_to_threat_reports(monitor.fetch_latest_signals())[0]
    alert = emitter.emit_alert(report)
    assert alert['is_critical'] is True
    assert "TOC ALERT" in alert['title']


def test_io_campaign_stix_and_graph_clustering():
    from shared.models import ThreatReport
    from sigtoc.bridge.policy_overlay import PolicyOverlayBridge

    io_report = ThreatReport(
        report_id="RPT-IO-RU-01",
        source="frontier_cti",
        title="Operation Bad Grammar IO Campaign",
        summary="State-linked coordinated inauthentic behavior using LLMs to seed disinformation narratives.",
        severity_score=8.5,
        credibility_score=0.95,
        relevance_score=0.90,
        threat_actors=["Storm-0821", "Bad Grammar Actor"],
        evasion_tactics=["synthetic persona generation", "narrative flooding"],
        campaign_type="influence_operation",
        state_nexus="RU",
        target_platforms=["social_feed", "api_llm"],
        recommended_policy_action="tighten_reach_gates",
    )

    bundle = STIXMapper.to_stix_bundle(io_report)
    # Bundle contains 1 campaign + 2 threat actors + 2 attack patterns = 5 objects
    assert len(bundle) == 5
    campaign = next(o for o in bundle if o.type == "campaign")
    assert campaign.name == "Operation Bad Grammar IO Campaign"
    assert "influence-operation" in campaign.labels
    assert "foreign-influence" in campaign.labels
    assert "state-nexus:ru" in campaign.labels

    actors = [o for o in bundle if o.type == "threat-actor"]
    assert len(actors) == 2
    assert all("influence-operator" in a.labels for a in actors)
    assert all("state-nexus:ru" in a.labels for a in actors)

    patterns = [o for o in bundle if o.type == "attack-pattern"]
    assert len(patterns) == 2
    assert all("influence-technique" in p.labels for p in patterns)

    # Fusion graph
    graph = ThreatEntityGraph()
    for obj in bundle:
        graph.add_threat_entity(obj)

    # Link actor to campaign, campaign to tactic
    graph.link_entities("Storm-0821", "Operation Bad Grammar IO Campaign", relationship="attributes-to")
    graph.link_entities("Operation Bad Grammar IO Campaign", "synthetic persona generation", relationship="employs-technique")
    graph.link_entities("Operation Bad Grammar IO Campaign", "narrative flooding", relationship="employs-technique")

    campaigns = graph.get_campaigns_for_actor("Storm-0821")
    assert campaigns == ["Operation Bad Grammar IO Campaign"]

    tactics = graph.get_tactics_for_campaign("Operation Bad Grammar IO Campaign")
    assert set(tactics) == {"synthetic persona generation", "narrative flooding"}

    clusters = graph.find_coordinated_clusters()
    assert len(clusters) >= 1

    # Policy overlay bridge
    overlay = PolicyOverlayBridge.generate_policy_overlay(io_report)
    assert overlay["metadata"]["campaign_type"] == "influence_operation"
    assert overlay["metadata"]["state_nexus"] == "RU"
    assert any(g["views"] == 50 and "quarantine" in g["action"] for g in overlay["reach_gates"])

    # Tactical alert emitter
    emitter = TacticalAlertEmitter()
    alert = emitter.emit_alert(io_report)
    assert alert["campaign_type"] == "influence_operation"
    assert alert["state_nexus"] == "RU"
    assert alert["is_critical"] is True
    assert "policy_overlay" in alert


def test_gtg_sector_targeting_and_travel_exposure():
    from sigtoc.picture import assess_traveler_exposure
    from shared.models import STIXThreatObject

    graph = ThreatEntityGraph()
    actor_obj = STIXThreatObject(
        id="threat-actor--gtg-20006",
        type="threat-actor",
        name="GTG-20006",
        description="Midnight Blizzard / JackPoterz",
        labels=["generative-threat-group", "cyber-espionage"],
    )
    graph.add_threat_entity(actor_obj)

    # Link to targeted sectors
    graph.link_entities("GTG-20006", "hospitality_vendors", relationship="targets-sector")
    graph.link_entities("GTG-20006", "drone_manufacturers", relationship="targets-sector")

    targeted_actors = graph.get_actors_targeting_sector("hospitality_vendors")
    assert targeted_actors == ["GTG-20006"]

    # Check traveler exposure evaluation
    actors_in_theater = [
        {
            "id": "act_gtg_20006",
            "name": "GTG-20006",
            "status": "active",
            "echelon": "state-nexus",
            "place": "Ukraine / Europe (RU nexus)",
            "aliases": ["Midnight Blizzard", "RU"],
            "ttps": ["CaptiveCrunch DNS hijacking", "Embassy Kit device code phishing"],
            "assessed_intent": "Traveler credential theft via hotel Wi-Fi and cloud tokens.",
        },
        {
            "id": "act_local_gang",
            "name": "Local Burglary Ring",
            "status": "active",
            "echelon": "local",
            "place": "London, UK",
            "aliases": ["London local"],
            "ttps": ["street robbery"],
            "assessed_intent": "Petty theft.",
        }
    ]

    # Test exposure for a trip to Europe with cyber interception filter
    exposed = assess_traveler_exposure("RU", actors_in_theater, capability_filter=["dns hijacking", "phishing"])
    assert len(exposed) == 1
    assert exposed[0]["name"] == "GTG-20006"
    assert "CaptiveCrunch DNS hijacking" in exposed[0]["ttps"]

