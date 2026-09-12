"""Tests for the Frontier AI Threat Intelligence collector (frontier_cti).
Verifies parsing of Anthropic September 2026 GTG disclosures and AI lab threat research,
country-scoped placement, offline/live modes, and STIX/ThreatReport generation."""
import os
import pytest

from sigtoc.collectors import frontier_cti
from sigtoc.collectors.registry import COLLECTORS, configured
from sigtoc.normalizer.stix_mapper import STIXMapper


def test_frontier_cti_sample_parsing():
    items = frontier_cti.parse_frontier_cti(frontier_cti.SAMPLE_DISCLOSURES)
    assert len(items) == 8
    assert all(i["source"] == "frontier_cti" for i in items)
    assert all(i["scope"] == "country" for i in items)

    # Check GTG-20006 (Midnight Blizzard / CaptiveCrunch)
    gtg_20006 = next(i for i in items if "GTG-20006" in i["title"])
    assert gtg_20006["country"] == "RU"
    assert gtg_20006["severity"] == "critical"
    assert gtg_20006["event_type"] == "cyber_espionage"
    assert "CaptiveCrunch" in gtg_20006["summary"]

    # Check GTG-27005 (Russia Drone Swarm)
    gtg_27005 = next(i for i in items if "GTG-27005" in i["title"])
    assert gtg_27005["country"] == "RU"
    assert gtg_27005["event_type"] == "conventional_weapons"

    # Check GTG-87001 (Yemen Guided Weapons)
    gtg_87001 = next(i for i in items if "GTG-87001" in i["title"])
    assert gtg_87001["country"] == "YE"
    assert gtg_87001["event_type"] == "conventional_weapons"

    # Check GTG-10007 (Hunan Exploit Foundry)
    gtg_10007 = next(i for i in items if "GTG-10007" in i["title"])
    assert gtg_10007["country"] == "CN"
    assert gtg_10007["event_type"] == "cyber_espionage"


def test_frontier_cti_to_threat_reports_and_stix():
    reports = frontier_cti.to_threat_reports(frontier_cti.SAMPLE_DISCLOSURES)
    assert len(reports) == 8

    # GTG-20006 STIX conversion
    r20006 = next(r for r in reports if "GTG-20006" in r.report_id)
    assert r20006.state_nexus == "RU"
    assert "hospitality_vendors" in r20006.targeted_sectors
    assert "CaptiveCrunch DNS hijacking" in r20006.evasion_tactics

    bundle_20006 = STIXMapper.to_stix_bundle(r20006)
    actors = [o for o in bundle_20006 if o.type == "threat-actor"]
    assert any(a.name == "GTG-20006" and "generative-threat-group" in a.labels for a in actors)
    patterns = [o for o in bundle_20006 if o.type == "attack-pattern"]
    assert any("CaptiveCrunch" in p.name and "supply-chain-interception" in p.labels for p in patterns)

    # GTG-27005 Drone Swarm STIX conversion
    r27005 = next(r for r in reports if "GTG-27005" in r.report_id)
    bundle_27005 = STIXMapper.to_stix_bundle(r27005)
    swarm_actors = [o for o in bundle_27005 if o.type == "threat-actor"]
    assert any("kinetic-adversary" in a.labels for a in swarm_actors)
    swarm_patterns = [o for o in bundle_27005 if o.type == "attack-pattern"]
    assert any("autonomous-weapons" in p.labels for p in swarm_patterns)


@pytest.mark.asyncio
async def test_frontier_cti_collection_placement(monkeypatch):
    monkeypatch.setenv("TOC_OFFLINE", "1")
    points = [(37.7749, -122.4194)]  # SF HQ
    # Requirements exist in Russia, China, and Yemen
    countries = {
        "RU": (55.7558, 37.6173),
        "CN": (39.9042, 116.4074),
        "YE": (15.3694, 44.1910),
    }

    placed = await frontier_cti.collect_frontier_cti(points, countries)
    assert len(placed) >= 3
    placed_countries = {p["country"] for p in placed}
    assert {"RU", "CN", "YE"}.issubset(placed_countries)

    ye_item = next(p for p in placed if p["country"] == "YE")
    assert ye_item["lat"] == 15.3694 and ye_item["lon"] == 44.1910
    assert ye_item["event_type"] == "conventional_weapons"


def test_frontier_cti_configured_honors_env(monkeypatch):
    monkeypatch.setenv("TOC_OFFLINE", "1")
    monkeypatch.delenv("TOC_SOURCES_CONFIGURED", raising=False)
    assert configured("frontier_cti") is False

    monkeypatch.delenv("TOC_OFFLINE", raising=False)
    assert configured("frontier_cti") is True

    monkeypatch.setenv("TOC_SOURCES_CONFIGURED", "gdacs,usgs")
    assert configured("frontier_cti") is False

    monkeypatch.setenv("TOC_SOURCES_CONFIGURED", "gdacs,frontier_cti")
    assert configured("frontier_cti") is True
