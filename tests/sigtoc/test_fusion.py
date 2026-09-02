from sigtoc.connectors.telegram_monitor import TelegramThreatMonitor
from sigtoc.normalizer.stix_mapper import STIXMapper
from sigtoc.fusion.graph import ThreatEntityGraph
from sigtoc.scoring.scorer import ThreatScorer
from sigtoc.alerting.emitter import TacticalAlertEmitter

def test_telegram_connector_and_scoring():
    monitor = TelegramThreatMonitor()
    raw = monitor.fetch_latest_signals()
    assert len(raw) == 1
    
    reports = monitor.parse_to_threat_reports(raw)
    assert len(reports) == 1
    report = reports[0]
    
    score = ThreatScorer.calculate_priority_score(report)
    assert score > 7.0
    assert ThreatScorer.is_critical_escalation(report) is True

def test_stix_normalization_and_entity_graph():
    monitor = TelegramThreatMonitor()
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
    monitor = TelegramThreatMonitor()
    report = monitor.parse_to_threat_reports(monitor.fetch_latest_signals())[0]
    alert = emitter.emit_alert(report)
    assert alert['is_critical'] is True
    assert "TOC ALERT" in alert['title']
