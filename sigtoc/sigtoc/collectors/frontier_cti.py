"""Frontier AI Threat Intelligence — Ingests public threat research and disruption reports
from frontier AI labs (Anthropic Threat Intel, OpenAI, Meta CTI) covering Influence Operations (IO),
cyber espionage (Generative Threat Groups / GTGs), and conventional weapons misuse.
Source reliability A/B. Country-scoped."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from shared.models import ThreatReport
from ..countries import to_iso
from .common import fetch, item, parse_iso, place_country_items, strip_html

FEED_URL = "https://www.anthropic.com/threat-intelligence-report-september-2026"

SAMPLE_DISCLOSURES: List[Dict[str, Any]] = [
    # --- Anthropic Sept 2026 GTG Disclosures ---
    {
        "id": "GTG-20006",
        "title": "GTG-20006: Russian Cyber Espionage, CaptiveCrunch Hotel DNS Hijacking, and Drone SDK Exfiltration",
        "summary": "Disrupted Russian state-nexus espionage actor (Midnight Blizzard / JackPoterz) using automated AI workflows for M365 device-code phishing (Embassy Kit), hotel guest Wi-Fi DNS hijacking (CaptiveCrunch) targeting travelers, and reverse-engineering military drone vision SDKs.",
        "threat_actors": ["GTG-20006", "Midnight Blizzard", "JackPoterz"],
        "state_nexus": "RU",
        "target_platforms": ["hotel_guest_wifi", "m365_cloud", "whatsapp_headless"],
        "targeted_sectors": ["defense_ministries", "drone_manufacturers", "hospitality_vendors", "diplomatic_missions"],
        "evasion_tactics": ["CaptiveCrunch DNS hijacking", "Embassy Kit device code phishing", "automated implant evasion loop"],
        "campaign_type": "cyber_espionage",
        "severity_score": 9.2,
        "credibility_score": 0.95,
        "relevance_score": 0.95,
        "recommended_policy_action": "flag_hotel_wifi_dns_hijack_risk_and_tighten_travel_brief",
        "published_at": "2026-09-08T10:00:00Z",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026#gtg-20006-russian-espionage",
    },
    {
        "id": "GTG-10007",
        "title": "GTG-10007: Autonomous Exploit Foundry and 13-Agent Collection Fleet in Hunan",
        "summary": "Disrupted sustained Chinese state-aligned operation running autonomous exploit foundries: automated firmware decompilation loop yielding appliance zero-days and a fleet of 13 standing collection agents scraping military/defense publications.",
        "threat_actors": ["GTG-10007"],
        "state_nexus": "CN",
        "target_platforms": ["network_appliances", "edtech_cloud", "gov_portals"],
        "targeted_sectors": ["security_appliance_vendors", "education_tech", "defense_publications"],
        "evasion_tactics": ["agent swarm decompile loop", "unattended open-source collection", "zero-day research"],
        "campaign_type": "cyber_espionage",
        "severity_score": 8.8,
        "credibility_score": 0.92,
        "relevance_score": 0.90,
        "recommended_policy_action": "audit_perimeter_appliances_and_block_recon_swarms",
        "published_at": "2026-09-08T10:00:00Z",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026#gtg-10007-exploit-foundries-and-autonomous-attack-frameworks",
    },
    {
        "id": "GTG-27005",
        "title": "GTG-27005: Autonomous Military Drone Swarm and Vision Guidance Engineering",
        "summary": "Disrupted Russian-nexus operation using Claude to engineer autonomous military drone swarm coordination, vision-based flight control, and automated target handoff algorithms.",
        "threat_actors": ["GTG-27005"],
        "state_nexus": "RU",
        "target_platforms": ["military_drone_firmware", "ai_vision_systems"],
        "targeted_sectors": ["tactical_convoys", "air_defense", "forward_operating_bases"],
        "evasion_tactics": ["drone swarm coordination", "autonomous targeting algorithms"],
        "campaign_type": "conventional_weapons",
        "severity_score": 9.5,
        "credibility_score": 0.95,
        "relevance_score": 0.95,
        "recommended_policy_action": "project_drone_swarm_threat_graphic_and_flag_route_vulnerability",
        "published_at": "2026-09-08T10:00:00Z",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026#gtg-27005-autonomous-drone-swarms",
    },
    {
        "id": "GTG-87001",
        "title": "GTG-87001: Yemen-Based Guided Weapons Software Engineering",
        "summary": "Disrupted Yemen-based engineering cell (Houthi nexus) using AI to develop missile guidance algorithms and precision strike flight-control software targeting shipping and regional bases.",
        "threat_actors": ["GTG-87001"],
        "state_nexus": "YE",
        "target_platforms": ["missile_guidance_firmware", "flight_control_units"],
        "targeted_sectors": ["maritime_shipping", "forward_operating_bases", "transit_corridors"],
        "evasion_tactics": ["guided strike flight control", "anti-ship missile targeting"],
        "campaign_type": "conventional_weapons",
        "severity_score": 9.4,
        "credibility_score": 0.94,
        "relevance_score": 0.92,
        "recommended_policy_action": "update_red_sea_danger_area_and_flight_corridors",
        "published_at": "2026-09-08T10:00:00Z",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026#gtg-87001-guided-weapons",
    },
    {
        "id": "GTG-50014",
        "title": "GTG-50014: ShinyHunters Industrial-Scale Credential Pipelines and Stolen API Compute",
        "summary": "Disrupted ShinyHunters affiliates (frkoo / MeowSHA) running automated AWS EC2 clusters decompiling 1.8M Android APKs, harvesting hardcoded secrets via TruffleHog, and stealing enterprise AI API keys to power secondary intrusions.",
        "threat_actors": ["GTG-50014", "ShinyHunters", "frkoo"],
        "state_nexus": "FR",
        "target_platforms": ["android_apk", "github_tokens", "telegram_carding"],
        "targeted_sectors": ["enterprise_saas", "telecom", "airlines"],
        "evasion_tactics": ["1.8M APK decompilation", "Telegram bot exfiltration", "stolen API key re-hosting"],
        "campaign_type": "cybercrime",
        "severity_score": 8.5,
        "credibility_score": 0.92,
        "relevance_score": 0.88,
        "recommended_policy_action": "rotate_exposed_api_tokens_and_audit_credential_stores",
        "published_at": "2026-09-08T10:00:00Z",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026#gtg-50014-shinyhunters-smash-and-grab-opportunists",
    },
    # --- Influence Operations Disclosures ---
    {
        "id": "FRONTIER-CTI-2026-001",
        "title": "Disruption of State-Linked Influence Operation 'Bad Grammar'",
        "summary": "Identified and disrupted an influence operation attributed to Russian state-sponsored actors using LLMs for multi-language persona generation, synthetic social media comments, and coordinated narrative flooding across platforms.",
        "threat_actors": ["Storm-0821", "Bad Grammar"],
        "state_nexus": "RU",
        "target_platforms": ["social_feed", "messaging", "api_llm"],
        "targeted_sectors": ["public_information", "election_discourse"],
        "evasion_tactics": ["synthetic persona generation", "narrative flooding", "token bypass"],
        "campaign_type": "influence_operation",
        "severity_score": 8.5,
        "credibility_score": 0.95,
        "relevance_score": 0.90,
        "recommended_policy_action": "tighten_reach_gates_and_flag_coordinated_clusters",
        "published_at": "2026-08-15T14:00:00Z",
        "url": "https://threat-intel.anthropic.com/disclosures/2026-001",
    },
    {
        "id": "FRONTIER-CTI-2026-002",
        "title": "Coordinated Inauthentic Behavior Network 'Spamouflage' LLM Tooling",
        "summary": "Disrupted clusters tied to Chinese state-aligned actors utilizing automated pipelines to translate political commentary, generate fake journalist personas, and astroturf discussions on international trade policy.",
        "threat_actors": ["Spamouflage", "Silk Typhoon"],
        "state_nexus": "CN",
        "target_platforms": ["social_feed", "video_comments"],
        "targeted_sectors": ["international_trade", "social_media"],
        "evasion_tactics": ["automated translation cycling", "persona astroturfing"],
        "campaign_type": "coordinated_inauthentic_behavior",
        "severity_score": 7.8,
        "credibility_score": 0.90,
        "relevance_score": 0.85,
        "recommended_policy_action": "enforce_mandatory_triage_on_clustered_accounts",
        "published_at": "2026-07-22T09:30:00Z",
        "url": "https://threat-intel.anthropic.com/disclosures/2026-002",
    },
    {
        "id": "FRONTIER-CTI-2026-003",
        "title": "Targeted Spear-Phishing and Influence Activity Attributed to Iranian Nexus",
        "summary": "Uncovered targeted reconnaissance and synthetic persona generation conducted by threat groups linked to Iranian intelligence targeting defense and diplomatic summits.",
        "threat_actors": ["Cotton Sandstorm", "Mint Sandstorm"],
        "state_nexus": "IR",
        "target_platforms": ["email", "social_feed"],
        "targeted_sectors": ["defense_summits", "diplomatic_corps"],
        "evasion_tactics": ["credential harvesting", "synthetic social proof"],
        "campaign_type": "influence_operation",
        "severity_score": 8.0,
        "credibility_score": 0.88,
        "relevance_score": 0.80,
        "recommended_policy_action": "route_to_security_triage",
        "published_at": "2026-06-10T11:15:00Z",
        "url": "https://threat-intel.anthropic.com/disclosures/2026-003",
    },
]


def parse_frontier_cti(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transforms raw CTI disclosure records into standard TOC Sigtoc threat item dicts."""
    out = []
    for d in data:
        country = to_iso(d.get("state_nexus") or "")
        severity_val = "critical" if d.get("severity_score", 0) >= 8.0 else "elevated"
        c_type = d.get("campaign_type", "influence_operation")
        if c_type in ("conventional_weapons", "guided_weapons", "drone_swarm"):
            ev_type = "conventional_weapons"
        elif c_type in ("cyber_espionage", "cybercrime"):
            ev_type = "cyber_espionage"
        elif c_type in ("influence_operation", "coordinated_inauthentic_behavior"):
            ev_type = "influence_op"
        else:
            ev_type = "threat_intel"

        out.append(
            item(
                external_id=f"frontier_cti:{d.get('id')}",
                title=d.get("title", "")[:140],
                summary=strip_html(d.get("summary") or d.get("title") or ""),
                lat=0.0,
                lon=0.0,
                radius_km=0.0,
                severity=severity_val,
                event_type=ev_type,
                source="frontier_cti",
                observed_at=parse_iso(d.get("published_at")),
                url=d.get("url"),
                country=country,
                scope="country",
            )
        )
    return out


def to_threat_reports(data: List[Dict[str, Any]]) -> List[ThreatReport]:
    """Converts disclosure records into normalized ThreatReport models."""
    out = []
    for d in data:
        out.append(
            ThreatReport(
                report_id=d.get("id") or f"RPT-CTI-{d.get('state_nexus', 'XX')}",
                source="frontier_cti",
                title=d.get("title", ""),
                summary=d.get("summary", ""),
                severity_score=float(d.get("severity_score", 7.0)),
                credibility_score=float(d.get("credibility_score", 0.9)),
                relevance_score=float(d.get("relevance_score", 0.85)),
                threat_actors=d.get("threat_actors", []),
                evasion_tactics=d.get("evasion_tactics", []),
                campaign_type=d.get("campaign_type", "influence_operation"),
                state_nexus=d.get("state_nexus"),
                target_platforms=d.get("target_platforms", []),
                targeted_sectors=d.get("targeted_sectors", []),
                recommended_policy_action=d.get("recommended_policy_action"),
                timestamp=parse_iso(d.get("published_at")),
            )
        )
    return out


def configured() -> bool:
    """Returns True if the source is active or can be collected."""
    if os.environ.get("TOC_OFFLINE", "") == "1":
        return False
    return True


async def collect_frontier_cti(points, countries: Dict[str, Any], max_km: float = 0.0) -> List[Dict[str, Any]]:
    """Collector execution hook: fetches live CTI disclosures if online, else returns placed sample items."""
    is_offline = os.environ.get("TOC_OFFLINE", "") == "1"
    raw_data: List[Dict[str, Any]] = []

    if is_offline or not os.environ.get("FRONTIER_CTI_LIVE_URL"):
        raw_data = SAMPLE_DISCLOSURES
    else:
        url = os.environ.get("FRONTIER_CTI_LIVE_URL", FEED_URL)
        r = await fetch(url, name="Frontier CTI")
        raw_data = r.json()

    items = parse_frontier_cti(raw_data)
    return place_country_items(items, countries)
